# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Doc Edit Game V2 environment server components."""

try:
    from .doc_edit_game_v2_environment import DocEditGameV2Environment
except Exception:
    DocEditGameV2Environment = None

__all__ = ["DocEditGameV2Environment"]
