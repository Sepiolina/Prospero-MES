import pytest
from prospero.ariel import ariel


class TestArielDatabase:
    """Test suite for the Ariel MES database module."""

    def test_set_and_get_simple_settings(self):
        """Test storing and retrieving simple primitive values."""
        ariel.set("station_settings", "scanner_port", "COM4")
        ariel.set("station_settings", "max_retries", 3)

        assert ariel.get("station_settings", "scanner_port") == "COM4"
        assert ariel.get("station_settings", "max_retries") == 3

    def test_set_and_update_complex_json(self):
        """Test storing, retrieving, and updating nested dictionary structures."""
        panel_sn = "SN-2026-XYZ-99"
        pcb_data = {
            "current_step": "SCANNING",
            "is_locked": False,
            "measurements": [],
            "operator": "Miranda Flores",
        }

        # Initial set
        ariel.set("active_cycles", panel_sn, pcb_data)

        # Fetch, update, and save
        current_state = ariel.get("active_cycles", panel_sn)
        current_state["current_step"] = "TESTING"
        current_state["is_locked"] = True
        current_state["measurements"].append({"voltage_v": 5.02, "status": "PASS"})

        ariel.set("active_cycles", panel_sn, current_state)

        # Verify nested update persists accurately
        updated_pcb = ariel.get("active_cycles", panel_sn)
        assert updated_pcb["current_step"] == "TESTING"
        assert updated_pcb["is_locked"] is True
        assert len(updated_pcb["measurements"]) == 1
        assert updated_pcb["measurements"][0]["voltage_v"] == 5.02
        assert updated_pcb["measurements"][0]["status"] == "PASS"

    def test_append_dynamic_logs(self):
        """Test the logging functionality for audit trails."""
        try:
            ariel.log(
                category="PLC_HANDSHAKE",
                level="INFO",
                message="Cycle complete signal received from PLC",
                meta={
                    "duration_ms": 1420,
                    "station_id": "STATION_01",
                    "final_status": "PASS",
                },
            )
        except Exception as e:
            pytest.fail(f"ariel.log raised an unexpected exception: {e}")

    def test_delete_key(self):
        """Test deletion of keys and verify they are correctly removed."""
        panel_sn = "SN-2026-XYZ-DELETE-TEST"

        # Setup: Ensure a record exists before deleting
        ariel.set("active_cycles", panel_sn, {"status": "temp_record"})

        # Action
        was_deleted = ariel.delete("active_cycles", panel_sn)

        # Assertions
        assert was_deleted is True, "Expected delete operation to return True."
        assert ariel.get("active_cycles", panel_sn, default="NOT_FOUND") == "NOT_FOUND"

    def test_get_fallback_defaults(self):
        """Test that retrieving a missing key safely returns the provided default value."""
        non_existent = ariel.get(
            "station_settings", "fake_key_name", default={"enabled": False}
        )

        assert isinstance(non_existent, dict)
        assert non_existent["enabled"] is False
