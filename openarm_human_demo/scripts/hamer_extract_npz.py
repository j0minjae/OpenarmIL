"""
hamer_extract_npz.py
=====================
chest mp4에서 추출한 프레임 폴더를 HaMeR로 추론해
프레임별 (keypoints_3d, vertices, is_right, cam_t) npz를 저장한다.

demo.py의 모델 로드/검출/추론 로직을 그대로 따르되(LazyConfig 기반 ViTDet
detectron2 설정, pred_cam 좌우 부호 반전 포함), 렌더링/오버레이 저장 대신
npz 저장으로 교체했다. 손 하나당 파일 하나: <frame_id>_<person_id>_<L|R>.npz

실행:
    python hamer_extract_npz.py \
        --img_folder frames/task01/episode_000 \
        --out_folder hamer_raw/task01/episode_000
"""

import argparse
import os
from pathlib import Path

import cv2
import numpy as np
import torch

from hamer.configs import CACHE_DIR_HAMER
from hamer.datasets.vitdet_dataset import ViTDetDataset
from hamer.models import DEFAULT_CHECKPOINT, download_models, load_hamer
from hamer.utils import recursive_to
from hamer.utils.renderer import cam_crop_to_full
from vitpose_model import ViTPoseModel


def build_detector(device, body_detector="vitdet"):
    """demo.py와 동일한 detectron2 기반 사람 검출기 로드."""
    from hamer.utils.utils_detectron2 import DefaultPredictor_Lazy

    if body_detector == "vitdet":
        from detectron2.config import LazyConfig

        import hamer

        cfg_path = Path(hamer.__file__).parent / "configs" / "cascade_mask_rcnn_vitdet_h_75ep.py"
        detectron2_cfg = LazyConfig.load(str(cfg_path))
        detectron2_cfg.train.init_checkpoint = (
            "https://dl.fbaipublicfiles.com/detectron2/ViTDet/COCO/cascade_mask_rcnn_vitdet_h/f328730692/model_final_f05665.pkl"
        )
        for i in range(3):
            detectron2_cfg.model.roi_heads.box_predictors[i].test_score_thresh = 0.25
        return DefaultPredictor_Lazy(detectron2_cfg)

    from detectron2 import model_zoo
    from detectron2.config import get_cfg

    detectron2_cfg = model_zoo.get_config("new_baselines/mask_rcnn_regnety_4gf_dds_FPN_400ep_LSJ.py", trained=True)
    detectron2_cfg.model.roi_heads.box_predictor.test_score_thresh = 0.5
    detectron2_cfg.model.roi_heads.box_predictor.test_nms_thresh = 0.4
    return DefaultPredictor_Lazy(detectron2_cfg)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--img_folder", type=str, required=True)
    parser.add_argument("--out_folder", type=str, required=True)
    parser.add_argument("--checkpoint", type=str, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--rescale_factor", type=float, default=2.0, help="demo.py 기본값과 동일")
    parser.add_argument("--body_detector", type=str, default="vitdet", choices=["vitdet", "regnety"])
    parser.add_argument("--file_type", nargs="+", default=["*.jpg", "*.png"])
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 1) HaMeR 모델 로드 (MANO_RIGHT.pkl 등이 _DATA/data/mano/에 있어야 함)
    download_models(CACHE_DIR_HAMER)
    model, model_cfg = load_hamer(args.checkpoint)
    model = model.to(device).eval()

    # 2) 사람 검출기 + 손 keypoint 검출기 (demo.py와 동일)
    detector = build_detector(device, args.body_detector)
    cpm = ViTPoseModel(device)

    out_folder = Path(args.out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)

    img_paths = sorted(img for end in args.file_type for img in Path(args.img_folder).glob(end))
    total_saved = 0

    for img_path in img_paths:
        frame_id = img_path.stem  # e.g. "000123", CSV frame_idx와 1:1 대응
        img_cv2 = cv2.imread(str(img_path))
        if img_cv2 is None:
            print(f"[{frame_id}] 이미지 로드 실패, skip")
            continue

        det_out = detector(img_cv2)
        img = img_cv2.copy()[:, :, ::-1]

        det_instances = det_out["instances"]
        valid_idx = (det_instances.pred_classes == 0) & (det_instances.scores > 0.5)
        pred_bboxes = det_instances.pred_boxes.tensor[valid_idx].cpu().numpy()
        pred_scores = det_instances.scores[valid_idx].cpu().numpy()

        if len(pred_bboxes) == 0:
            continue  # 사람 검출 실패 -> npz 저장 안 함 (alignment 단계에서 skip 처리됨)

        vitposes_out = cpm.predict_pose(
            img,
            [np.concatenate([pred_bboxes, pred_scores[:, None]], axis=1)],
        )

        bboxes, is_right_list = [], []
        for vitposes in vitposes_out:
            left_hand_kp = vitposes["keypoints"][-42:-21]
            right_hand_kp = vitposes["keypoints"][-21:]
            for hand_kp, is_right in [(left_hand_kp, 0), (right_hand_kp, 1)]:
                valid_kp = hand_kp[:, 2] > 0.5
                if valid_kp.sum() > 3:
                    bbox = [
                        hand_kp[valid_kp, 0].min(), hand_kp[valid_kp, 1].min(),
                        hand_kp[valid_kp, 0].max(), hand_kp[valid_kp, 1].max(),
                    ]
                    bboxes.append(bbox)
                    is_right_list.append(is_right)

        if len(bboxes) == 0:
            continue

        boxes = np.stack(bboxes)
        right_flags = np.array(is_right_list)

        dataset = ViTDetDataset(model_cfg, img_cv2, boxes, right_flags, rescale_factor=args.rescale_factor)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

        saved_this_frame = 0
        for batch in dataloader:
            batch = recursive_to(batch, device)
            with torch.no_grad():
                out = model(batch)

            # demo.py와 동일: 손 좌우에 따라 pred_cam의 y 성분 부호를 뒤집은 뒤 cam_crop_to_full로 투영
            multiplier = 2 * batch["right"] - 1
            pred_cam = out["pred_cam"]
            pred_cam[:, 1] = multiplier * pred_cam[:, 1]
            box_center = batch["box_center"].float()
            box_size = batch["box_size"].float()
            img_size = batch["img_size"].float()
            scaled_focal_length = model_cfg.EXTRA.FOCAL_LENGTH / model_cfg.MODEL.IMAGE_SIZE * img_size.max()
            pred_cam_t_full = (
                cam_crop_to_full(pred_cam, box_center, box_size, img_size, scaled_focal_length).detach().cpu().numpy()
            )

            batch_size = batch["img"].shape[0]
            for n in range(batch_size):
                person_id = int(batch["personid"][n])
                is_right = bool(batch["right"][n].cpu().item())

                keypoints_3d = out["pred_keypoints_3d"][n].detach().cpu().numpy()
                vertices = out["pred_vertices"][n].detach().cpu().numpy()
                # demo.py의 verts[:,0] = (2*is_right-1)*verts[:,0]와 동일한 좌우 반전 관례.
                # keypoints_3d는 demo.py에서 직접 쓰이지 않지만 동일한 MANO mesh 좌표계이므로
                # vertices와 같은 규칙으로 반전한다 (왼손을 오른손 템플릿의 mirror로 저장).
                if not is_right:
                    keypoints_3d[:, 0] *= -1
                    vertices[:, 0] *= -1

                save_path = out_folder / f"{frame_id}_{person_id}_{'R' if is_right else 'L'}.npz"
                np.savez(
                    save_path,
                    keypoints_3d=keypoints_3d,
                    vertices=vertices,
                    is_right=is_right,
                    cam_t=pred_cam_t_full[n],
                )
                saved_this_frame += 1

        total_saved += saved_this_frame
        print(f"[{frame_id}] {saved_this_frame}개 손 -> npz 저장")

    print(f"완료: {len(img_paths)}개 프레임 중 {total_saved}개 npz 저장 -> {out_folder}")


if __name__ == "__main__":
    main()
