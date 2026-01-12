"""Vaillant sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import VaillantClient
from .const import CONF_DID, DISPATCHERS, DOMAIN, EVT_DEVICE_CONNECTED, API_CLIENT
from .entity import VaillantEntity

_LOGGER = logging.getLogger(__name__)

# =========================
# 传感器定义（不动）
# =========================
SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key="Room_Temperature_Setpoint_Comfort",
        name="Room temperature setpoint of comfort mode",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Room_Temperature_Setpoint_ECO",
        name="Room temperature setpoint of ECO mode",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Outdoor_Temperature",
        name="Outdoor temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Room_Temperature",
        name="Room temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="DHW_setpoint",
        name="Domestic hot water setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Lower_Limitation_of_CH_Setpoint",
        name="Lower limitation of central heating setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Upper_Limitation_of_CH_Setpoint",
        name="Upper limitation of central heating setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Lower_Limitation_of_DHW_Setpoint",
        name="Lower limitation of domestic hot water",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Upper_Limitation_of_DHW_Setpoint",
        name="Upper limitation of domestic hot water",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Current_DHW_Setpoint",
        name="Current domestic hot water setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Flow_Temperature_Setpoint",
        name="Flow temperature setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Flow_temperature",
        name="Flow temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="return_temperature",
        name="Return flow temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="Tank_temperature",
        name="Water tank temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


# =========================
# setup 逻辑（关键修改）
# =========================
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Vaillant sensors."""

    device_id = entry.data.get(CONF_DID)
    client: VaillantClient = hass.data[DOMAIN][API_CLIENT][entry.entry_id]

    added_entities: list[str] = []

    @callback
    def async_new_entities(device_attrs: dict[str, Any]):
        """Create ALL sensor entities once, regardless of current data."""
        _LOGGER.debug("setup vaillant sensor entities (force create all)")

        new_entities = []

        for description in SENSOR_DESCRIPTIONS:
            if description.key not in added_entities:
                new_entities.append(
                    VaillantSensorEntity(client, description)
                )
                added_entities.append(description.key)

        if new_entities:
            async_add_entities(new_entities)

    # 设备连上就一次性创建所有实体
    unsub = async_dispatcher_connect(
        hass,
        EVT_DEVICE_CONNECTED.format(device_id),
        async_new_entities,
    )

    hass.data[DOMAIN][DISPATCHERS][device_id].append(unsub)

    return True


# =========================
# Sensor 实体（关键修改）
# =========================
class VaillantSensorEntity(VaillantEntity, SensorEntity):
    """Define a Vaillant sensor entity."""

    def __init__(
        self,
        client: VaillantClient,
        description: SensorEntityDescription,
    ):
        super().__init__(client)
        self.entity_description = description

        # 关键：默认认为设备可用
        self._attr_available = True

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return f"{self.device.id}_{self.entity_description.key}"

    @callback
    def update_from_latest_data(self, data: dict[str, Any]) -> None:
        """Update the entity from the latest data.

        - 如果当前数据缺失：保留旧值
        - 不因为 None 进入 unavailable
        """

        value = data.get(self.entity_description.key)

        if value is not None:
            self._attr_native_value = value

        # 只要设备在线，就认为传感器可用
        self._attr_available = True
