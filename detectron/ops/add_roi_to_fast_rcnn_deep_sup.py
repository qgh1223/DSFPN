# Copyright (c) 2017-present, Facebook, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np

from detectron.core.config import cfg
from detectron.datasets import json_dataset
from detectron.datasets import roidb as roidb_utils
import detectron.modeling.FPN as fpn

import detectron.roi_data.fast_rcnn_deep_sup as roi_deep_sup_data

import detectron.utils.blob as blob_utils

# import pydevd
class AddRoiDeepSupOp(object):
    def __init__(self, train):
        self._train = train
    def forward(self, inputs, outputs):
        """See modeling.detector.CollectAndDistributeFpnRpnProposals for
        inputs/outputs documentation.
        """
        # pydevd.settrace(suspend=False, trace_only_current_thread=True)
        rois = inputs[0].data
        if cfg.MODEL.MASK_RCNN_DEEP_SUP_ON:
            mask_rois = inputs[2].data
        if self._train:
            label=inputs[1].data
            if cfg.MODEL.MASK_RCNN_DEEP_SUP_ON:
                roi_has_mask = inputs[3].data
                masks= inputs[4].data
            output_blob_names = roi_deep_sup_data.get_roi_deep_sup_blob_names()
            blobs = {k: [] for k in output_blob_names}
            if cfg.MODEL.MASK_RCNN_DEEP_SUP_ON:
                roi_deep_sup_data.add_roi_deep_sup_blobs(blobs, rois,label,mask_rois,roi_has_mask,masks)
            else:
                roi_deep_sup_data.add_roi_deep_sup_blobs(blobs, rois, label)

            for i, k in enumerate(output_blob_names):
                blob_utils.py_op_copy_blob(blobs[k], outputs[i])
        else:
            distribute(rois, outputs)

def distribute(rois, outputs):
    """To understand the output blob order see return value of
    detectron.roi_data.fast_rcnn.get_fast_rcnn_blob_names(is_training=False)
    """
    lvl_min = cfg.FPN.ROI_MIN_LEVEL
    lvl_max = cfg.FPN.ROI_MAX_LEVEL
    lvls = fpn.map_rois_to_fpn_levels(rois[:, 1:5], lvl_min, lvl_max)

    outputs[0].reshape(rois.shape)
    outputs[0].data[...] = rois

    # Create new roi blobs for each FPN level
    # (See: modeling.FPN.add_multilevel_roi_blobs which is similar but annoying
    # to generalize to support this particular case.)
    rois_idx_order = np.empty((0, ))
    for output_idx, lvl in enumerate(range(lvl_min, lvl_max + 1)):
        idx_lvl = np.where(lvls == lvl)[0]
        blob_roi_level = rois[idx_lvl, :]
        outputs[output_idx + 1].reshape(blob_roi_level.shape)
        outputs[output_idx + 1].data[...] = blob_roi_level
        rois_idx_order = np.concatenate((rois_idx_order, idx_lvl))
    rois_idx_restore = np.argsort(rois_idx_order)
    blob_utils.py_op_copy_blob(rois_idx_restore.astype(np.int32), outputs[-1])


