import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app as mdm_app


class FakeIAMResponse:
    status_code = 200

    def json(self):
        return {
            "id": "test-user",
            "is_active": True,
            "permissions": [mdm_app.READ_PERMISSION, mdm_app.WRITE_PERMISSION],
        }


class ProductionMasterDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(mdm_app.app)
        cls.iam_patch = patch("iam_client.httpx.get", return_value=FakeIAMResponse())
        cls.iam_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.iam_patch.stop()

    def setUp(self):
        c = mdm_app.connect()
        try:
            c.execute("DELETE FROM mdm_records WHERE domain_code LIKE 'PROD_%'")
            c.execute("DELETE FROM mdm_domains WHERE code LIKE 'PROD_%'")
            ts = time.time()
            for code, name in [
                ("PROD_MATERIAL", "Production Materials"),
                ("PROD_BOM", "Bills of Material"),
                ("PROD_WORK_CENTER", "Production Work Centers"),
                ("PROD_ROUTING", "Production Routings"),
                ("PROD_VERSION", "Production Versions"),
            ]:
                c.execute(
                    mdm_app.sql("INSERT INTO mdm_domains(id,code,name,description,is_active,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)"),
                    (f"domain-{code}", code, name, "", 1, "test-user", ts, ts),
                )
            c.commit()
        finally:
            c.close()

    def post(self, path, payload):
        return self.client.post(path, json=payload, headers={"Authorization": "Bearer test"})

    def get(self, path):
        return self.client.get(path, headers={"Authorization": "Bearer test"})

    def seed_complete_master(self):
        self.assertEqual(201, self.post("/v1/production/materials", {
            "material_code": "FG-BIKE", "name": "Finished Bike", "base_uom": "EA", "material_type": "finished"
        }).status_code)
        self.assertEqual(201, self.post("/v1/production/materials", {
            "material_code": "RM-FRAME", "name": "Bike Frame", "base_uom": "EA", "material_type": "raw"
        }).status_code)
        self.assertEqual(201, self.post("/v1/production/work-centers", {
            "work_center_code": "WC-ASSEMBLY", "name": "Assembly", "capacity_units_per_hour": 12, "status": "active"
        }).status_code)
        self.assertEqual(201, self.post("/v1/production/boms", {
            "bom_code": "BOM-BIKE-001", "output_material_code": "FG-BIKE", "base_quantity": 1,
            "components": [{"material_code": "RM-FRAME", "quantity": 1, "uom": "EA"}], "status": "active"
        }).status_code)
        self.assertEqual(201, self.post("/v1/production/routings", {
            "routing_code": "RT-BIKE-001", "output_material_code": "FG-BIKE",
            "operations": [{"sequence": 10, "operation_code": "ASSEMBLE", "work_center_code": "WC-ASSEMBLY", "standard_minutes": 5}],
            "status": "active"
        }).status_code)

    def test_production_version_requires_active_references(self):
        response = self.post("/v1/production/production-versions", {
            "version_code": "PV-BIKE-001",
            "material_code": "FG-BIKE",
            "bom_code": "BOM-BIKE-001",
            "routing_code": "RT-BIKE-001",
            "status": "active",
        })
        self.assertEqual(400, response.status_code)
        self.assertEqual("production_master_reference_invalid", response.json()["detail"])

    def test_create_and_read_complete_production_version(self):
        self.seed_complete_master()
        version = self.post("/v1/production/production-versions", {
            "version_code": "PV-BIKE-001",
            "material_code": "FG-BIKE",
            "bom_code": "BOM-BIKE-001",
            "routing_code": "RT-BIKE-001",
            "status": "active",
        })
        self.assertEqual(201, version.status_code)
        read = self.get("/v1/production/versions/PV-BIKE-001")
        self.assertEqual(200, read.status_code)
        self.assertEqual("FG-BIKE", read.json()["material_code"])
        self.assertEqual("BOM-BIKE-001", read.json()["bom_code"])
        self.assertEqual("RT-BIKE-001", read.json()["routing_code"])


if __name__ == "__main__":
    unittest.main()
