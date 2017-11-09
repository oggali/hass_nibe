import logging
import time
import asyncio

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.core import callback
from homeassistant.helpers.entity import (Entity, async_generate_entity_id)
from homeassistant.helpers.entity import Entity
from homeassistant.const import TEMP_CELSIUS
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.helpers.dispatcher import async_dispatcher_connect

DEPENDENCIES = ['nibe']
DOMAIN       = 'nibe'
_LOGGER      = logging.getLogger(__name__)


CONF_SYSTEM    = 'system'
CONF_PARAMETER = 'parameter'

SIGNAL_UPDATE  = 'nibe_update'

PLATFORM_SCHEMA = vol.Schema({
        vol.Required(CONF_SYSTEM): cv.string,
        vol.Required(CONF_PARAMETER): cv.string,
    }, extra=vol.ALLOW_EXTRA)

SCALE = {
        '°C' 		: { 'scale' : 10,   'unit': TEMP_CELSIUS, 	'icon': None },
        'A'  		: { 'scale' : 10,   'unit': 'A', 		'icon': 'mdi:power-plug' },
        'DM' 		: { 'scale' : 10,   'unit': 'DM', 		'icon': None },
        'kW' 		: { 'scale' : 100,  'unit': 'kW', 		'icon': None },
        'Hz' 		: { 'scale' : 10,   'unit': 'Hz', 		'icon': 'mdi:update' },
        '%' 		: { 'scale' : 1,    'unit': '%', 		'icon': None },
        'h'		: { 'scale' : 1,    'unit': 'h',                'icon': 'mdi:clock' },
        'öre/kWh'	: { 'scale' : 100,  'unit': 'kr/MWh',		'icon': None },
}


SCALE_DEFAULT = { 'scale': None, 'unit': None, 'icon': None }

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):

    sensors = None
    if (discovery_info):
        sensors = [ NibeSensor(hass, parameter['system_id'], parameter['parameter_id']) for parameter in discovery_info ]
    else:
        sensors = [ NibeSensor(hass, config.get(CONF_SYSTEM), config.get(CONF_PARAMETER)) ]

    async_add_devices(sensors, True)

class NibeSensor(Entity):
    def __init__(self, hass, system_id, parameter_id):
        """Initialize the Nibe sensor."""
        self._state        = None
        self._system_id    = system_id
        self._parameter_id = parameter_id
        self._name         = "{}_{}".format(system_id, parameter_id)
        self._unit         = None
        self._data         = None
        self._icon         = None
        self.entity_id     = async_generate_entity_id(
                                ENTITY_ID_FORMAT,
                                self._name,
                                hass=hass)

    @asyncio.coroutine
    def async_added_to_hass(self):
        async_dispatcher_connect(self.hass, SIGNAL_UPDATE, self.update_callback)

    @callback
    def update_callback(self):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        return self._icon

    @property
    def should_poll(self):
        """No polling needed."""
        return True

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'designation'  : self._data['designation'],
            'parameter_id' : self._data['parameterId'],
            'display_value': self._data['displayValue'],
            'raw_value'    : self._data['rawValue'],
            'display_unit' : self._data['unit'],
        }

    @property
    def available(self):
        """Return True if entity is available."""
        if self._state == None:
            return False
        else:
            return True

    @asyncio.coroutine
    def async_update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """

        data = yield from self.hass.data[DOMAIN].uplink.get_parameter_data(self._system_id, self._parameter_id)
        print(data)
        if data:

            self._name  = data['title']

            scale = SCALE.get(data['unit'], SCALE_DEFAULT)
            self._icon  = scale['icon']
            self._unit  = scale['unit']
            if data['displayValue'] == '--':
                self._state = None
            elif scale['scale']:
                self._state = data['rawValue'] / scale['scale']
            else:
                self._state = data['displayValue']

            self._data = data

        else:
            self._state = None


