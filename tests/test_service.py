import tempfile
import unittest
from pathlib import Path

from app.service import TramService


class TramServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = TramService(Path(self.temp_dir.name) / "test.db")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_orients_known_procedure_and_keeps_traceability(self) -> None:
        result = self.service.submit(
            {
                "citizen_name": "Ana Perez",
                "email": "ana@example.com",
                "description": "Necesito renovar mi cedula vencida.",
                "documents": [
                    {"name": "Cedula de identidad", "valid": True},
                    {"name": "Comprobante de pago", "valid": True},
                ],
            }
        )

        self.assertEqual(result["status"], "ORIENTADO")
        self.assertFalse(result["human_review"])
        self.assertEqual(result["procedure_type"], "renovacion_cedula")
        self.assertEqual(result["guide"]["missing_documents"], [])
        self.assertEqual(len(result["traceability"]), 4)

    def test_unknown_procedure_is_sent_to_human_review(self) -> None:
        result = self.service.submit(
            {
                "citizen_name": "Luis Mora",
                "email": "luis@example.com",
                "description": "Quiero resolver un caso administrativo que no esta en el catalogo.",
                "documents": [],
            }
        )

        self.assertEqual(result["status"], "DERIVADO_A_FUNCIONARIO")
        self.assertTrue(result["human_review"])
        self.assertEqual(result["procedure_type"], None)
        self.assertEqual(len(self.service.database.pending_human_reviews()), 1)

    def test_manual_escalation_updates_request(self) -> None:
        created = self.service.submit(
            {
                "citizen_name": "Sofia Diaz",
                "email": "sofia@example.com",
                "description": "Necesito certificado de antecedentes.",
                "documents": [],
            }
        )
        result = self.service.escalate(created["id"], "Caso con datos inconsistentes.")

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "DERIVADO_A_FUNCIONARIO")
        self.assertTrue(result["human_review"])
        self.assertEqual(result["traceability"][-1]["action"], "derivar")


if __name__ == "__main__":
    unittest.main()
