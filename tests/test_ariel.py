import pytest
import os
import sys
from prospero.ariel import ariel
from pathlib import Path


class TestArielDatabase:
    """Test suite for the Ariel MES database module."""

    def test_encryption_module_compilation_state(self):
        """Verify that the core security logic is running as a compiled C binary in production.

        If ARIEL_DEV_MODE is set, we allow raw Python/bytecode. Otherwise, we enforce
        that the underlying backend is compiled (.pyd or .so).
        """
        backend_module = sys.modules.get("prospero.ariel.encryption")
        assert backend_module is not None, (
            "The core encryption backend (encryption) was not loaded!"
        )

        backend_file = backend_module.__file__
        assert backend_file is not None, (
            "Loaded module does not have a physical file path!"
        )

        backend_path = Path(backend_file)
        file_extension = backend_path.suffix.lower()
        is_dev_mode = os.environ.get("ARIEL_DEV_MODE") == "1"

        if is_dev_mode:
            assert file_extension in [".py", ".pyc"], (
                f"Expected raw Python in Dev Mode, but imported compiled binary: {backend_path.name}. "
                f"Please remove old binaries from your workspace to avoid shadowing changes!"
            )
            print(
                f"\n[INFO] Dev Mode verification successful. Loaded: {backend_path.name}"
            )
        else:
            assert file_extension in [".pyd", ".so"], (
                f"CRITICAL SECURITY FAIL: The core security module is running as uncompiled Python source code "
                f"({backend_path.name})! Compile it to a binary native extension before packaging."
            )
            print(
                f"\n[INFO] Production Security verification successful. Loaded compiled binary: {backend_path.name}"
            )

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
