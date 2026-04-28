from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.selector import selector
from homeassistant.core import HomeAssistant

from aioeloverblik import EloverblikClient

from .const import (
    DOMAIN,
    CONF_API_TOKEN,
    CONF_METERING_POINT,
    CONF_SAVEEYE_ENERGY,
    CONF_SAVEEYE_POWER,
)

_LOGGER = logging.getLogger(__name__)


# =========================
# HELPERS
# =========================
def _format_metering_point_label(m) -> str:
    """Create readable label for MPID."""
    try:
        street = getattr(m, "street_name", "")
        number = getattr(m, "building_number", "")
        city = getattr(m, "city_name", "")

        address = " ".join(filter(None, [street, number, city])).strip()

        if address:
            return f"{address} ({m.metering_point_id})"
    except Exception:
        pass

    return f"{m.metering_point_id}"


async def _create_client(hass: HomeAssistant, token: str) -> EloverblikClient:
    """Create client safely (avoids blocking SSL in event loop)."""

    def _factory():
        return EloverblikClient(refresh_token=token)

    return await hass.async_add_executor_job(_factory)


# =========================
# CONFIG FLOW
# =========================
class EloverblikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Step 1: input token."""

        if user_input is not None:
            token = user_input[CONF_API_TOKEN]

            try:
                client = await _create_client(self.hass, token)

                async with client:
                    mps = await client.get_metering_points()

                if not mps:
                    raise ValueError("No metering points found")

                self._token = token
                self._mp_options = {
                    _format_metering_point_label(m): m.metering_point_id
                    for m in mps
                }

                return await self.async_step_select_mpid()

            except Exception as err:
                _LOGGER.error("Login failed: %s", err)

                return self.async_show_form(
                    step_id="user",
                    data_schema=self._schema_token(),
                    errors={"base": "auth"},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema_token(),
        )

    def _schema_token(self):
        return vol.Schema(
            {
                vol.Required(CONF_API_TOKEN): str,
            }
        )

    # =========================
    # STEP 2: MPID + SENSORS
    # =========================
    async def async_step_select_mpid(self, user_input=None):

        if user_input is not None:
            return self.async_create_entry(
                title=f"Eloverblik {user_input[CONF_METERING_POINT]}",
                data={
                    CONF_API_TOKEN: self._token,
                    **user_input,
                },
            )

        return self.async_show_form(
            step_id="select_mpid",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_METERING_POINT): selector(
                        {
                            "select": {
                                "options": [
                                    {"label": k, "value": v}
                                    for k, v in self._mp_options.items()
                                ],
                                "mode": "dropdown",
                            }
                        }
                    ),
                    vol.Optional(CONF_SAVEEYE_ENERGY): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "device_class": "energy",
                            }
                        }
                    ),
                    vol.Optional(CONF_SAVEEYE_POWER): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "device_class": "power",
                            }
                        }
                    ),
                }
            ),
        )


# =========================
# OPTIONS FLOW
# =========================
class EloverblikOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SAVEEYE_ENERGY,
                        default=self.config_entry.options.get(
                            CONF_SAVEEYE_ENERGY,
                            self.config_entry.data.get(CONF_SAVEEYE_ENERGY),
                        ),
                    ): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "device_class": "energy",
                            }
                        }
                    ),
                    vol.Optional(
                        CONF_SAVEEYE_POWER,
                        default=self.config_entry.options.get(
                            CONF_SAVEEYE_POWER,
                            self.config_entry.data.get(CONF_SAVEEYE_POWER),
                        ),
                    ): selector(
                        {
                            "entity": {
                                "domain": "sensor",
                                "device_class": "power",
                            }
                        }
                    ),
                }
            ),
        )


async def async_get_options_flow(config_entry):
    return EloverblikOptionsFlow(config_entry)