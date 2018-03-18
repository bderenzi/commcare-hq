from __future__ import absolute_import
from __future__ import unicode_literals
import logging
from django.utils.translation import ugettext_lazy as _


LOG_LEVEL_CHOICES = (
    (99, 'Disable logging'),
    (logging.ERROR, 'Error'),
    (logging.INFO, 'Info'),
)

IMPORT_FREQUENCY_WEEKLY = 'weekly'
IMPORT_FREQUENCY_MONTHLY = 'monthly'
IMPORT_FREQUENCY_CHOICES = (
    (IMPORT_FREQUENCY_WEEKLY, _('Weekly')),
    (IMPORT_FREQUENCY_MONTHLY, _('Monthly')),
)

# The Location property to store the OpenMRS location UUID in:
LOCATION_OPENMRS_UUID = 'openmrs_uuid'

# To match cases against their OpenMRS Person UUID, set the patient_identifier's key to the value of
# PERSON_UUID_IDENTIFIER_TYPE_ID. To match against any other OpenMRS identifier, set the patient_identifier's
# key to the UUID of the OpenMRS Identifier Type.
PERSON_UUID_IDENTIFIER_TYPE_ID = 'uuid'
