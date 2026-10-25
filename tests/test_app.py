import os
import uuid

import pytest

from sysmon.app import acquire_single_instance


@pytest.mark.skipif(os.name != "nt", reason="Windows named mutex")
def test_single_instance_guard():
    name = f"Local\\SysMonTest-{uuid.uuid4()}"
    assert acquire_single_instance(name) is True
    assert acquire_single_instance(name) is False
