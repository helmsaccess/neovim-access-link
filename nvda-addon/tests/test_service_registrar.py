from __future__ import annotations

import unittest

from nvim_nvda_core import ServiceRegistrar


class ServiceRegistrarTests(unittest.TestCase):
    def test_only_matching_service_and_token_can_unpublish(self) -> None:
        registrar = ServiceRegistrar()
        first = object()
        second = object()
        first_token = registrar.publish(first)
        second_token = registrar.publish(second)

        self.assertIs(second, registrar.current)
        self.assertFalse(registrar.unpublish(first, first_token))
        self.assertIs(second, registrar.current)
        self.assertFalse(registrar.unpublish(second, first_token))
        self.assertIs(second, registrar.current)
        self.assertTrue(registrar.unpublish(second, second_token))
        self.assertIsNone(registrar.current)

    def test_publish_requires_a_service(self) -> None:
        registrar = ServiceRegistrar()
        with self.assertRaisesRegex(ValueError, "service is required"):
            registrar.publish(None)


if __name__ == "__main__":
    unittest.main()
