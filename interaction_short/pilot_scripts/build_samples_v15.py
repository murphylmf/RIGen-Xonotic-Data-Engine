                      
"""Stage-2 v15 wrapper for the short-video visual and visibility fixes.

All capture, action, accelerated replay, prompt, telemetry, and temporal-
visibility behavior remains in the proven v13/v12 pipeline.  This isolated
wrapper only narrows the tolerant frustum used for visibility labels.  The
transient-effect clock fix lives in the revision-locked engine build.
"""

from __future__ import annotations

from . import build_samples_v12 as _base


                                                                         
                                                                      
                              
_base.FRUSTUM_TOLERANCE_SCALE = 1.04

from .build_samples_v13 import *                        
