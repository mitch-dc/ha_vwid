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
# TODO: write classes for all properties, instead of one
    _LOGGER.warn(coordinator.data['data']['batteryStatus']['currentSOC_pct'])
    async_add_entities(
        [
            VwIdSocSensor(coordinator, api.vin),
            VwIdCurrentRangeSensor(coordinator, api.vin),
            VwIdRemainingChargingTimeSensor(coordinator, api.vin),
            VwIdChargingStateSensor(coordinator, api.vin),
            VwIdChargeModeSensor(coordinator, api.vin),
            VwIdChargePowerSensor(coordinator, api.vin),
            VwIdChargeRateSensor(coordinator, api.vin),
            VwIdMaxChargeCurrentACSensor(coordinator, api.vin),
            VwIdAutoUnlockPlugWhenChargedSensor(coordinator, api.vin),
            VwIdTargetStateOfChargeSensor(coordinator, api.vin),
            VwIdPlugConnectionStateSensor(coordinator, api.vin),
            VwIdPlugLockStateSensor(coordinator, api.vin),
            VwIdRemainingClimatisationTimeSensor(coordinator, api.vin),
            VwIdRemainingClimatisationStateSensor(coordinator, api.vin),

            VwIdTargetTemperatureFSensor(coordinator, api.vin),
            VwIdTargetTemperatureKSensor(coordinator, api.vin),
            VwIdTargetTemperatureCSensor(coordinator, api.vin),

            VwIdClimatisationWithoutExternalPowerSensor(coordinator, api.vin),
            VwIdClimatizationAtUnlockSensor(coordinator, api.vin),
            VwIdWindowHeatingSensor(coordinator, api.vin),
            VwIdZoneFrontLeftEnabledSensor(coordinator, api.vin),
            VwIdZoneFrontRightEnabledSensor(coordinator, api.vin), 
            
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
    def state(self) -> bool:
        return self.coordinator.data['data']['chargingSettings']['autoUnlockPlugWhenCharged'] == 'true'
        
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
    def state(self) -> bool:
        return self.coordinator.data['data']['climatisationSettings']['climatizationAtUnlock'] == 'true'

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

class VwIdRemainingClimatisationTimeSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Remaining Climatisation Time'
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
    def unit_of_measurement(self):
        return 'min'

    @property
    def state(self):
        return self.coordinator.data['data']['climatisationStatus']['remainingClimatisationTime_min']

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

class VwIdRemainingClimatisationStateSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Climatisation State'
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
        return self.coordinator.data['data']['climatisationStatus']['climatisationState']

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

class VwIdZoneFrontLeftEnabledSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Zone Front Left Enabled'
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
    def state(self) -> bool:
        return self.coordinator.data['data']['climatisationSettings']['zoneFrontLeftEnabled'] == 'true'

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

class VwIdZoneFrontRightEnabledSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Zone Front Right Enabled'
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
    def state(self) -> bool:
        return self.coordinator.data['data']['climatisationSettings']['zoneFrontRightEnabled'] == 'true'

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

class VwIdTargetTemperatureCSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Target Temperature C'
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
        return self.coordinator.data['data']['climatisationSettings']['targetTemperature_C']
        #return self._state
        
    @property
    def device_class(self):
        return DEVICE_CLASS_TEMPERATURE

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return '°C'

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

class VwIdTargetTemperatureKSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Target Temperature K'
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
        return self.coordinator.data['data']['climatisationSettings']['targetTemperature_K']
        #return self._state
        
    @property
    def device_class(self):
        return DEVICE_CLASS_TEMPERATURE

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return 'K'

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

class VwIdTargetTemperatureFSensor(CoordinatorEntity):
    def __init__(self, coordinator, vin):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)
        self._name = 'Volkswagen ID Target Temperature F'
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
        return self.coordinator.data['data']['climatisationSettings']['targetTemperature_F']
        #return self._state
        
    @property
    def device_class(self):
        return DEVICE_CLASS_TEMPERATURE

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def unit_of_measurement(self):
        return '°F'

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
