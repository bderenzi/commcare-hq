from datetime import datetime
import os, json

from django.http import HttpRequest
from django.test import TestCase

from bihar.reports.due_list import VaccinationSummary, get_due_list_by_task_name, get_due_list_records
from corehq.apps.users.models import WebUser
from corehq.apps.users.models import CommCareUser, CommCareCase
from dimagi.utils.couch.database import get_db

from ..beneficiary import Beneficiary
from ..reports import BeneficiaryPaymentReport, IncentivePaymentReport

DIR_PATH = os.path.abspath(os.path.dirname(__file__))
test_data_location = os.path.join(DIR_PATH, 'opm_test.json')

fixtures_loaded = False


class OPMTestBase(object):

    def load_fixtures(self):
        self.db = get_db()
        with open(test_data_location) as f:
            docs = json.loads(f.read())
        for doc in docs:
            self.db.save_doc(doc)

    def setUp(self):
        global fixtures_loaded
        if not fixtures_loaded:
            fixtures_loaded = True
            self.load_fixtures()
        self.postSetUp()

    def postSetUp(self):
        return

    def test_all_results(self):
        for row in self.get_rows(): 
            row_object = self.report.model(row)
            for method, result in row['test_results']:
                self.assertEquals(
                    str(getattr(row_object, method)),
                    str(result)
                )


class TestBeneficiary(OPMTestBase, TestCase):
    report = BeneficiaryPaymentReport
    
    def get_rows(self):
        return CommCareCase.get_all_cases('opm', include_docs=True)


class TestIncentive(OPMTestBase, TestCase):
    report = IncentivePaymentReport

    def get_rows(self):
        return CommCareUser.by_domain('opm')
