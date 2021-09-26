from .libvwid import vwid
import asyncio
import logging
import aiohttp
import voluptuous as vol
from datetime import timedelta
from typing import Any, Callable, Dict, Optional
from homeassistant import config_entries, core
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    ENTITY_ID_FORMAT,
)
from homeassistant.const import (
    ATTR_NAME,
    CONF_NAME,
    CONF_PASSWORD,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
)
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from .const import (
    DOMAIN,
    CONF_VIN
)

import async_timeout

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]

    session = async_get_clientsession(hass)
    api = vwid(session)
    api.set_credentials(config[CONF_NAME], config[CONF_PASSWORD])
    api.set_vin(config[CONF_VIN])


    async def async_update_data():
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(30):

                data = await api.get_status()
                if (data):
                    _LOGGER.warn(data)
                    return data
                else:
                    _LOGGER.exception("Error retrieving data")
        except ApiAuthError as err:
            # Raising ConfigEntryAuthFailed will cancel future updates
            # and start a config flow with SOURCE_REAUTH (async_step_reauth)
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name = "VW ID Sensor",
        update_method = async_update_data,
        update_interval = timedelta(seconds=30),
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    _LOGGER.warn(coordinator.data['data']['batteryStatus']['currentSOC_pct'])
    async_add_entities(
        [
            VwIdSensor(coordinator, api.vin, "State Of Charge", '%', coordinator.data['data']['batteryStatus']['currentSOC_pct'], DEVICE_CLASS_BATTERY),
            VwIdSensor(coordinator, api.vin, "Current Range In KM", 'km', coordinator.data['data']['batteryStatus']['cruisingRangeElectric_km'], None),
            
            VwIdSensor(coordinator, api.vin, "Remaining Charging Time", 'minutes', coordinator.data['data']['chargingStatus']['remainingChargingTimeToComplete_min'], None),
            VwIdSensor(coordinator, api.vin, "Charging State", '', coordinator.data['data']['chargingStatus']['chargingState'], None),
            VwIdSensor(coordinator, api.vin, "Charge Mode", '', coordinator.data['data']['chargingStatus']['chargeMode'], None),
            VwIdSensor(coordinator, api.vin, "Charge Power In kW", 'kW', coordinator.data['data']['chargingStatus']['chargePower_kW'], DEVICE_CLASS_POWER),
            VwIdSensor(coordinator, api.vin, "Charge Rate In km/h", 'km/h', coordinator.data['data']['chargingStatus']['chargeRate_kmph'], None),

            VwIdSensor(coordinator, api.vin, "Max Charge Current AC", '', coordinator.data['data']['chargingSettings']['maxChargeCurrentAC'], None),
            VwIdSensor(coordinator, api.vin, "Auto Unlock Plug When Charged", '', coordinator.data['data']['chargingSettings']['autoUnlockPlugWhenCharged'], None),
            VwIdSensor(coordinator, api.vin, "Target State Of Charge", '%', coordinator.data['data']['chargingSettings']['targetSOC_pct'], DEVICE_CLASS_BATTERY),

            VwIdSensor(coordinator, api.vin, "Max Charge Current AC", '', coordinator.data['data']['plugStatus']['plugConnectionState'], None),
            VwIdSensor(coordinator, api.vin, "Max Charge Current AC", '', coordinator.data['data']['plugStatus']['plugLockState'], None),

            VwIdSensor(coordinator, api.vin, "Remaining Climatisation Time", 'minutes', coordinator.data['data']['climatisationStatus']['remainingClimatisationTime_min'], None),
            VwIdSensor(coordinator, api.vin, "Climatisation State", '', coordinator.data['data']['climatisationStatus']['climatisationState'], None),

            VwIdSensor(coordinator, api.vin, "Target Temperature C", '°C', coordinator.data['data']['climatisationSettings']['targetTemperature_C'], DEVICE_CLASS_TEMPERATURE),
            VwIdSensor(coordinator, api.vin, "Target Temperature K", 'K', coordinator.data['data']['climatisationSettings']['targetTemperature_K'], DEVICE_CLASS_TEMPERATURE),             
            VwIdSensor(coordinator, api.vin, "Target Temperature F", '°F', coordinator.data['data']['climatisationSettings']['targetTemperature_F'], DEVICE_CLASS_TEMPERATURE),  
            VwIdSensor(coordinator, api.vin, "Unit In Car", '', coordinator.data['data']['climatisationSettings']['unitInCar'], None),
            VwIdSensor(coordinator, api.vin, "Climatisation Without External Power", '', coordinator.data['data']['climatisationSettings']['climatisationWithoutExternalPower'], None),  
            VwIdSensor(coordinator, api.vin, "Climatization At Unlock", '', coordinator.data['data']['climatisationSettings']['climatizationAtUnlock'], None),
            VwIdSensor(coordinator, api.vin, "Window Heating Enabled", '', coordinator.data['data']['climatisationSettings']['windowHeatingEnabled'], None),  
            VwIdSensor(coordinator, api.vin, "Zone Front Left Enabled", '', coordinator.data['data']['climatisationSettings']['zoneFrontLeftEnabled'], None),
            VwIdSensor(coordinator, api.vin, "Zone Front Right Enabled", '', coordinator.data['data']['climatisationSettings']['zoneFrontRightEnabled'], None),  
        ]
    )

class VwIdSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin, name, unit_of_measurement, apiData, device_class):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID' + ' ' + name
        self._state = apiData
        self._available = True
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + name
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement
        
        _LOGGER.warn(self._entity_id)

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._entity_id

    @property
    def state(self):
        return self._state
        
    @property
    def device_class(self):
        return self._device_class
        
    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement