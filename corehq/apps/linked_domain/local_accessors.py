from corehq import toggles, feature_previews
from corehq.apps.custom_data_fields.dbaccessors import get_by_domain_and_type
from corehq.apps.locations.views import LocationFieldsView
from corehq.apps.products.views import ProductFieldsView


def get_toggles_previews(domain):
    return {
        'toggles': list(toggles.toggles_dict(domain=domain)),
        'previews': list(feature_previews.previews_dict(domain=domain))
    }


def get_custom_data_models(domain):
    fields = {}
    for field_view in [LocationFieldsView, ProductFieldsView, LocationFieldsView]:
        model = get_by_domain_and_type(domain, field_view.field_type)
        if model:
            fields[field_view.field_type] = model.to_json()['fields']
    return fields
