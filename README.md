I'm not working on this integration anymore, moved to a new library:
https://github.com/mitch-dc/volkswagen_we_connect_id



# Volkswagen ID component for Home Assistant

forked from skagmo/ha_vwid

## Home Assistant component installation

* (Activate We Connect using the official app)
* Add content of "custom_components/vwid" in this repository to the custom_components subfolder in your Home Assistant configuration folder
* Go to integrations and search for "Volkswagen ID"
* Fill in email, password and VIN as used in your app
* There should now be a list of sensors entity

## Library

"custom\_components/vwid/libvwid.py" contains the Python class to communicate with the We Connect ID API used by the ID series electric cars. See libvwid_example.py in the same folder for usage.


