"""Validate a local harness profile without generating answers or benchmark scores."""
import json
from pathlib import Path
from pydantic import ValidationError
from harnessprobe.profile import HarnessProfile,load_profile
from harnessprobe.adapters.openai_compat import OpenAICompatAdapter
profile=load_profile(str(Path(__file__).with_name('presentation-profile.yaml')))
adapter=OpenAICompatAdapter(profile,api_key='')
rejected=False
try:HarnessProfile.model_validate({**profile.model_dump(),'reasoning_effort':'unsupported'})
except ValidationError:rejected=True
print(json.dumps({'model_id':profile.model_id,'vendor':profile.vendor,'max_tokens':profile.max_tokens,
                  'stop_tokens':profile.stop_tokens,'published_score':profile.published_score,
                  'adapter_is_stub_without_key':adapter.is_stub,'invalid_effort_rejected':rejected},indent=2))
assert rejected and adapter.is_stub
