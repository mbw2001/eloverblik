from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.util import dt as dt_util

from homeassistant.const import UnitOfEnergy

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
# SETUP
# =========================
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:

    data = entry.data
    options = entry.options

    coordinator = EloverblikCoordinator(
        hass,
        token=data[CONF_API_TOKEN],
        mpid=data[CONF_METERING_POINT],
        saveeye_energy=options.get(
            CONF_SAVEEYE_ENERGY,
            data.get(CONF_SAVEEYE_ENERGY),
        ),
        saveeye_power=options.get(
            CONF_SAVEEYE_POWER,
            data.get(CONF_SAVEEYE_POWER),
        ),
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [EloverblikEnergyTodaySensor(coordinator, data[CONF_METERING_POINT])]
    )


# =========================
# COORDINATOR
# =========================
class EloverblikCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, token, mpid, saveeye_energy, saveeye_power):
        super().__init__(
            hass,
            _LOGGER,
            name="Eloverblik",
            update_interval=timedelta(minutes=5),
        )

        self.token = token
        self.mpid = mpid
        self.saveeye_energy = saveeye_energy
        self.saveeye_power = saveeye_power

    async def _async_update_data(self):
        def _create_client():
            return EloverblikClient(refresh_token=self.token)

        client = await self.hass.async_add_executor_job(_create_client)

        async with client:
            ts = await client.get_time_series(
                [self.mpid],
                aggregation="Quarter",
            )

        eloverblik = _filter_today(_flatten_points(ts))
        saveeye = _get_saveeye_points(
            self.hass,
            self.saveeye_energy,
            self.saveeye_power,
        )

        merged = _merge(eloverblik, saveeye)

        return {
            "total": sum(p["value"] for p in merged),
        }


# =========================
# SENSOR
# =========================
class EloverblikEnergyTodaySensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = "energy"
    _attr_state_class = "total_increasing"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator, mpid):
        super().__init__(coordinator)
        self._attr_unique_id = f"eloverblik_energy_{mpid}"
        self._attr_name = "Eloverblik Energy Today"

    @property
    def native_value(self):
        return self.coordinator.data["total"]


# =========================
# MERGE
# =========================
def _merge(api: List[dict], saveeye: List[dict]) -> List[dict]:
    result: Dict[datetime, dict] = {}

    for p in saveeye:
        result[p["time"]] = p

    for p in api:
        result[p["time"]] = p

    return list(result.values())


# =========================
# SAVEEYE (simplified)
# =========================
def _get_saveeye_points(hass, energy_entity, power_entity):
    points = []
    now = dt_util.now().replace(minute=0, second=0, microsecond=0)

    if energy_entity:
        state: State = hass.states.get(energy_entity)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                val = float(state.state) / 1000
                points.append({"time": now, "value": val})
            except Exception:
                pass

    if power_entity:
        state: State = hass.states.get(power_entity)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                val = float(state.state)
                kwh = val / 1000 / 4  # approx 15 min
                points.append({"time": now, "value": kwh})
            except Exception:
                pass

    return points


# =========================
# FLATTEN
# =========================
def _flatten_points(data: Any) -> List[dict]:
    points = []

    for doc in data:
        for ts in doc.time_series:
            for period in ts.periods:
                start = datetime.fromisoformat(period.start.replace("Z", "+00:00"))
                step = timedelta(minutes=15)

                for p in period.points:
                    ts = start + step * (int(p.position) - 1)
                    ts = dt_util.as_local(ts)

                    points.append(
                        {
                            "time": ts,
                            "value": float(p.quantity),
                        }
                    )

    return points


def _filter_today(points):
    today = dt_util.now().date()
    return [p for p in points if p["time"].date() == today]