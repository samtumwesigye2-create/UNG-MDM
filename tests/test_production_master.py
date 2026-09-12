import unittest

from production_master import (
    ProductionMasterValidationError,
    validate_bom,
    validate_production_version,
    validate_routing,
    validate_work_center,
)


class ProductionMasterValidationTests(unittest.TestCase):
    def test_bom_requires_at_least_one_positive_component(self):
        with self.assertRaisesRegex(ProductionMasterValidationError, "bom_components_required"):
            validate_bom({"material_code": "FG-001", "components": []})

        with self.assertRaisesRegex(ProductionMasterValidationError, "component_quantity_must_be_positive"):
            validate_bom({
                "material_code": "FG-001",
                "components": [{"material_code": "RM-001", "quantity": 0}],
            })

    def test_routing_requires_ordered_operations_and_work_center(self):
        with self.assertRaisesRegex(ProductionMasterValidationError, "routing_operations_required"):
            validate_routing({"material_code": "FG-001", "operations": []})

        result = validate_routing({
            "material_code": "FG-001",
            "operations": [
                {"sequence": 20, "operation_code": "PACK", "work_center_code": "WC-PACK"},
                {"sequence": 10, "operation_code": "ASSEMBLE", "work_center_code": "WC-ASSEMBLY"},
            ],
        })
        self.assertEqual([10, 20], [op["sequence"] for op in result["operations"]])

    def test_work_center_requires_capacity(self):
        with self.assertRaisesRegex(ProductionMasterValidationError, "capacity_must_be_positive"):
            validate_work_center({"code": "WC-01", "capacity_per_hour": 0})

    def test_production_version_requires_all_master_references(self):
        with self.assertRaisesRegex(ProductionMasterValidationError, "production_version_references_required"):
            validate_production_version({
                "material_code": "FG-001",
                "bom_code": "",
                "routing_code": "ROUT-001",
                "work_center_code": "WC-01",
            })


if __name__ == "__main__":
    unittest.main()
