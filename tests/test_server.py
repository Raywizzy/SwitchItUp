import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


class ServerSessionTests(unittest.TestCase):
    def test_valid_session_header_selects_session_state_id(self):
        session_id = "session_0123456789abcdef"

        self.assertEqual(server.resolve_state_id({server.SESSION_HEADER: session_id}), session_id)

    def test_invalid_session_header_falls_back_to_default_state(self):
        self.assertEqual(server.resolve_state_id({server.SESSION_HEADER: "../../bad"}), server.DEFAULT_STATE_ID)
        self.assertEqual(server.resolve_state_id({}), server.DEFAULT_STATE_ID)

    def test_local_session_store_uses_isolated_json_file(self):
        with tempfile.TemporaryDirectory() as tempdir:
            data_path = Path(tempdir) / "state.json"
            session_id = "session_0123456789abcdef"
            with patch.dict("os.environ", {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}):
                with patch.object(server, "DATA_PATH", data_path):
                    store = server.build_store(session_id)

        self.assertEqual(store.path.name, f"state-{session_id}.json")


if __name__ == "__main__":
    unittest.main()
