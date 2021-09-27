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
    DEVICE_CLASS_TIMESTAMP,
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
# TODO: write classes for all properties, instead of one
    _LOGGER.warn(coordinator.data['data']['batteryStatus']['currentSOC_pct'])
    async_add_entities(
        [
            

            VwIdSocSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "State Of Charge", '%', coordinator.data['data']['batteryStatus']['currentSOC_pct'], DEVICE_CLASS_BATTERY),
            #VwIdSensor(coordinator, api.vin, "Car Captured Timestamp", '', coordinator.data['data']['batteryStatus']['carCapturedTimestamp'], DEVICE_CLASS_TIMESTAMP),            
            
            VwIdCurrentRangeSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Current Range In KM", 'km', coordinator.data['data']['batteryStatus']['cruisingRangeElectric_km'], None),
            
            VwIdRemainingChargingTimeSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Remaining Charging Time", 'minutes', coordinator.data['data']['chargingStatus']['remainingChargingTimeToComplete_min'], None),
            
            VwIdChargingStateSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Charging State", '', coordinator.data['data']['chargingStatus']['chargingState'], None),
            
            VwIdChargeModeSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Charge Mode", '', coordinator.data['data']['chargingStatus']['chargeMode'], None),
            
            VwIdChargePowerSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Charge Power In kW", 'kW', coordinator.data['data']['chargingStatus']['chargePower_kW'], DEVICE_CLASS_POWER),
            
            VwIdChargeRateSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Charge Rate In km/h", 'km/h', coordinator.data['data']['chargingStatus']['chargeRate_kmph'], None),

            VwIdMaxChargeCurrentACSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Max Charge Current AC", '', coordinator.data['data']['chargingSettings']['maxChargeCurrentAC'], None),

            VwIdAutoUnlockPlugWhenChargedSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Auto Unlock Plug When Charged", '', coordinator.data['data']['chargingSettings']['autoUnlockPlugWhenCharged'], None),
            
            VwIdTargetStateOfChargeSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Target State Of Charge", '%', coordinator.data['data']['chargingSettings']['targetSOC_pct'], DEVICE_CLASS_BATTERY),

            VwIdPlugConnectionStateSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Plug Connection State", '', coordinator.data['data']['plugStatus']['plugConnectionState'], None),

            VwIdPlugLockStateSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Plug Lock State", '', coordinator.data['data']['plugStatus']['plugLockState'], None),


            #VwIdSensor(coordinator, api.vin, "Remaining Climatisation Time", 'minutes', coordinator.data['data']['climatisationStatus']['remainingClimatisationTime_min'], None),
            #VwIdSensor(coordinator, api.vin, "Climatisation State", '', coordinator.data['data']['climatisationStatus']['climatisationState'], None),

            #VwIdSensor(coordinator, api.vin, "Target Temperature C", '°C', coordinator.data['data']['climatisationSettings']['targetTemperature_C'], DEVICE_CLASS_TEMPERATURE),
            #VwIdSensor(coordinator, api.vin, "Target Temperature K", 'K', coordinator.data['data']['climatisationSettings']['targetTemperature_K'], DEVICE_CLASS_TEMPERATURE),             
            #VwIdSensor(coordinator, api.vin, "Target Temperature F", '°F', coordinator.data['data']['climatisationSettings']['targetTemperature_F'], DEVICE_CLASS_TEMPERATURE),  
            #VwIdSensor(coordinator, api.vin, "Unit In Car", '', coordinator.data['data']['climatisationSettings']['unitInCar'], None),


            VwIdClimatisationWithoutExternalPowerSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Climatisation Without External Power", '', coordinator.data['data']['climatisationSettings']['climatisationWithoutExternalPower'], None),  
            
            VwIdClimatizationAtUnlockSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Climatization At Unlock", '', coordinator.data['data']['climatisationSettings']['climatizationAtUnlock'], None),
            
            
            VwIdWindowHeatingSensor(coordinator, api.vin),
            #VwIdSensor(coordinator, api.vin, "Window Heating Enabled", '', coordinator.data['data']['climatisationSettings']['windowHeatingEnabled'], None),  
              
            
            
            #VwIdSensor(coordinator, api.vin, "Zone Front Left Enabled", '', coordinator.data['data']['climatisationSettings']['zoneFrontLeftEnabled'], None),
            #VwIdSensor(coordinator, api.vin, "Zone Front Right Enabled", '', coordinator.data['data']['climatisationSettings']['zoneFrontRightEnabled'], None),  
            
        ],
        True
    )

class VwIdWindowHeatingSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Window Heating Enabled'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['climatisationSettings']['windowHeatingEnabled']
        #return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """

        await self.coordinator.async_request_refresh()

class VwIdSocSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID State Of Charge'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['batteryStatus']['currentSOC_pct']
        #return self._state
        
    @property
    def device_class(self):
        return DEVICE_CLASS_BATTERY

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return '%'

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()

class VwIdCurrentRangeSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Current Range In KM'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['batteryStatus']['cruisingRangeElectric_km']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return 'km'

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()

class VwIdRemainingChargingTimeSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Remaining Charging Time'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingStatus']['remainingChargingTimeToComplete_min']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return 'minutes'

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()

class VwIdChargingStateSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Charging State'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingStatus']['chargingState']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()

class VwIdChargeModeSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Charge Mode'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingStatus']['chargeMode']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()

class VwIdChargePowerSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Charge Power'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingStatus']['chargePower_kW']
        #return self._state
        
    @property
    def device_class(self):
        return DEVICE_CLASS_POWER

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return 'kW'

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()

class VwIdChargeRateSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Charge Rate'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingStatus']['chargeRate_kmph']
        #return self._state
        
    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return 'km/h'

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()

class VwIdMaxChargeCurrentACSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Max Charge Current AC'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingSettings']['maxChargeCurrentAC']
        #return self._state
        
    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return 'km/h'

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()

class VwIdAutoUnlockPlugWhenChargedSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Auto Unlock Plug When Charged'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingSettings']['autoUnlockPlugWhenCharged']
        #return self._state
        
    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()

class VwIdTargetStateOfChargeSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Target State Of Charge'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['chargingSettings']['targetSOC_pct']
        
    @property
    def device_class(self):
        return DEVICE_CLASS_BATTERY

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return '%'

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        await self.coordinator.async_request_refresh()

class VwIdPlugConnectionStateSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Plug Connection State'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['plugStatus']['plugConnectionState']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()

class VwIdPlugLockStateSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Plug Lock State'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['plugStatus']['plugLockState']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()        

class VwIdClimatisationWithoutExternalPowerSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Climatisation Without External Power'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['climatisationSettings']['climatisationWithoutExternalPower']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()      

class VwIdClimatizationAtUnlockSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Climatization At Unlock'
        self.attrs = {'vin': vin}
        self._entity_id = vin + "_" + self._name   

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
        return self.coordinator.data['data']['climatisationSettings']['climatizationAtUnlock']

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """
        
        await self.coordinator.async_request_refresh()      

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

    @property
    def should_poll(self) -> bool:
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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

    async def async_update(self):
        """Update the entity.
        Only used by the generic entity update service.
        """

        _LOGGER.warn("Update running")
        await self.coordinator.async_request_refresh()