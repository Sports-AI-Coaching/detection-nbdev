# AUTOGENERATED! DO NOT EDIT! File to edit: 00_dataset.ipynb (unless otherwise specified).

__all__ = ['XMLDetectionDataset', 'CLASSES', 'XMLDetectionDataModule']

# Cell
import os

import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader
import warnings
import torchvision
from torchvision.datasets import MNIST, ImageFolder
from torchvision.transforms import ToTensor, Resize, Compose, CenterCrop, Normalize
import pytorch_lightning as pl
from pytorch_lightning.metrics.functional import classification, f1
from pytorch_lightning.loggers import TensorBoardLogger
from rich.progress import track
import fastai.vision.augment
import fastai.vision.data
from cv2 import cv2
import matplotlib.pyplot as plt
from rich import print

import collections
import os
import tarfile
import xml.etree.ElementTree as ET

# from torchvision.utils import download_url, check_integrity, verify_str_arg
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import random
import torch
from PIL import Image, ImageDraw
from pl_bolts.utils import _TORCHVISION_AVAILABLE
from pl_bolts.utils.warnings import warn_missing_pkg
from pytorch_lightning import LightningDataModule
from torch.utils.data import DataLoader
from torchvision.datasets.vision import VisionDataset

if _TORCHVISION_AVAILABLE:
    from torchvision import transforms as transform_lib
    from torchvision.datasets import VOCDetection
else:  # pragma: no cover
    warn_missing_pkg("torchvision")

# Cell

CLASSES = ["soccer_ball"]

class XMLDetectionDataset(VisionDataset):
    """`Pascal VOC <http://host.robots.ox.ac.uk/pascal/VOC/>`_ Detection Dataset.

    Args:
        root (string): Root directory of the VOC Dataset.
        image_transform (callable, optional): A function/transform that  takes in an PIL image
            and returns a transformed version. E.g, ``transforms.RandomCrop``
        target_transform (callable, required): A function/transform that takes in the
            target and transforms it.
        transforms (callable, optional): A function/transform that takes input sample and its target as entry
            and returns a transformed version.
    """

    def __init__(
        self,
        root: str,
        image_transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
        transform: Optional[Callable] = None,
    ):
        super(XMLDetectionDataset, self).__init__(root)
        self.root = Path(root)
        self.image_transform = image_transform
        self.target_transform = target_transform
        self.transform = transform

        self.image_files = sorted(list(self.root.glob("*.jpg")))
        self.xml_files = sorted(list(self.root.glob("*.xml")))

        assert len(self.image_files) == len(self.xml_files),\
            f"{len(self.image_files), len(self.xml_files)}"

    def __getitem__(self, index: int) -> Tuple[Any, Any]:
        """
        Args:
            index (int): Index

        Returns:
            tuple: (image, target) where target is a dictionary of the XML tree.
        """
        img = Image.open(str(self.image_files[index])).convert("RGB")
        target = self.parse_xml(ET.parse(str(self.xml_files[index])).getroot())
        bbox = self.parse_bbox(target)

        if self.image_transform:
            img = self.image_transform(img)
        if self.target_transform:
            bbox = self.target_transform(bbox)
        if self.transform is not None:
            transformed = self.transform(image=img, bboxes=bbox)
            img = transformed['image']
            bbox = transformed['bboxes']

        return img, bbox

    def __len__(self) -> int:
        return len(self.image_files)

    def parse_xml(self, node: ET.Element) -> Dict[str, Any]:
        xml_dict: Dict[str, Any] = {}
        children = list(node)
        if children:
            def_dic: Dict[str, Any] = collections.defaultdict(list)
            for dc in map(self.parse_xml, children):
                for ind, v in dc.items():
                    def_dic[ind].append(v)
            if node.tag == "annotation":
                def_dic["object"] = [def_dic["object"]]
            xml_dict = {
                node.tag: {
                    ind: v[0] if len(v) == 1 else v for ind, v in def_dic.items()
                }
            }
        if node.text:
            text = node.text.strip()
            if not children:
                xml_dict[node.tag] = text
        return xml_dict

    def parse_bbox(self, xml):
        bboxes = xml['annotation']['object']
#         assert len(bboxes) >= 1, f'File contains no/more than one instance of ball: {xml}'
        try:
            bbox = bboxes[0]['bndbox']
            xmin = int(bbox['xmin'])
            ymin = int(bbox['ymin'])
            xmax = int(bbox['xmax'])
            ymax = int(bbox['ymax'])

            return [xmin, ymin, xmax, ymax]
        except IndexError:
            return None

    def draw_sample(self, idx=None):
        if idx is None:
            idx = random.choice(range(0, len(self)))

        img = Image.open(str(self.image_files[idx])).convert("RGB")
        target = self.parse_xml(ET.parse(str(self.xml_files[idx])).getroot())
        x0, y0, x1, y1 = self.parse_bbox(target)

        draw = ImageDraw.Draw(img)
        draw.rectangle([x0, y0, x1, y1])
        return img
#     @staticmethod
#     def visualize_bbox(img, bbox, class_name, color=(255, 0, 0) , thickness=2):
#         """Visualizes a single bounding box on the image"""
#         BOX_COLOR = (255, 0, 0) # Red
#         TEXT_COLOR = (255, 255, 255) # White

#         x_min, y_min, w, h = bbox
#         x_min, x_max, y_min, y_max = int(x_min), int(x_min + w), int(y_min), int(y_min + h)

#         cv2.rectangle(img, (x_min, y_min), (x_max, y_max), color=color, thickness=thickness)

#         ((text_width, text_height), _) = cv2.getTextSize(class_name, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
#         cv2.rectangle(img, (x_min, y_min - int(1.3 * text_height)), (x_min + text_width, y_min), BOX_COLOR, -1)
#         cv2.putText(
#             img,
#             text=class_name,
#             org=(x_min, y_min - int(0.3 * text_height)),
#             fontFace=cv2.FONT_HERSHEY_SIMPLEX,
#             fontScale=0.35,
#             color=TEXT_COLOR,
#             lineType=cv2.LINE_AA,
#         )
#         return img

#     @staticmethod
#     def visualize(image, bboxes, category_ids, category_id_to_name, ax=None):
#         if ax is None:
#             fig, ax = plt.subplots()
#         img = image.copy()
#         for bbox, category_id in zip(bboxes, category_ids):
#             if bbox != []:
#                 class_name = category_id_to_name[category_id]
#                 img = XMLDetectionDataset.visualize_bbox(img, bbox, class_name)
#         ax.axis('off')
#         ax.imshow(img)

# Cell

class XMLDetectionDataModule(LightningDataModule):
    def __init__(
        self,
        data_dir: str,
        r_train: float =None,
        r_val: float = None,
        r_test: float = None,
        num_workers: int = 16,
        normalize: bool = False,
        shuffle: bool = False,
        pin_memory: bool = False,
        drop_last: bool = False,
        transform=None,
        image_transform=None,
        target_transform=None,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        super().__init__(*args, **kwargs)

        self.data_dir = data_dir
        self.r_train = r_train
        self.r_val = r_val
        self.r_test = r_test
        self.num_workers = num_workers
        self.normalize = normalize
        self.shuffle = shuffle
        self.pin_memory = pin_memory
        self.drop_last = drop_last
        self.transform = transform
        self.image_transform = image_transform
        self.target_transform = target_transform

    def setup(self, mode="fit") -> None:
        if mode == 'use_dir':
            self.trainset = XMLDetectionDataset(
                os.path.join(self.data_dir, 'train'),
                transform=self.transform,
                image_transform=self.image_transform,
                target_transform=self.target_transform)
            self.valset = XMLDetectionDataset(
                os.path.join(self.data_dir, 'valid'),
                transform=self.transform,
                image_transform=self.image_transform,
                target_transform=self.target_transform)
            self.testset = XMLDetectionDataset(
                os.path.join(self.data_dir, 'test'),
                transform=self.transform,
                image_transform=self.image_transform,
                target_transform=self.target_transform)
        else:
            dataset = XMLDetectionDataset(self.data_dir,
                                          transform=self.transform,
                                          image_transform=self.image_transform,
                                          target_transform=self.target_transform)

            n_train = int(len(dataset) * self.r_train)
            n_val = int((len(dataset) - n_train) * self.r_val/ (self.r_test + self.r_val))
            n_test = len(dataset) - n_train - n_val

            self.trainset, self.valset, self.testset = torch.utils.data.random_split(
                dataset, [n_train, n_val, n_test],
            )

    def train_dataloader(
        self,
        batch_size: int = 32,
        image_transforms: Union[List[Callable], Callable] = None,
    ) -> DataLoader:
        """
        VOCDetection train set uses the `train` subset
        Args:
            batch_size: size of batch
            transforms: custom transforms
        """
        return DataLoader(
            self.trainset,
            batch_size=batch_size,
            shuffle=self.shuffle,
            num_workers=self.num_workers,
            drop_last=self.drop_last,
            pin_memory=self.pin_memory,
            collate_fn=self._collate_fn,
        )

    def val_dataloader(
        self, batch_size: int = 32, image_transforms: Optional[List[Callable]] = None
    ) -> DataLoader:
        """
        VOCDetection val set uses the `val` subset
        Args:
            batch_size: size of batch
            transforms: custom transforms
        """
        return DataLoader(
            self.valset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            drop_last=self.drop_last,
            pin_memory=self.pin_memory,
            collate_fn=self._collate_fn,
        )

    def test_dataloader(
        self, batch_size: int = 1, image_transforms: Optional[List[Callable]] = None
    ) -> DataLoader:
        """
        VOCDetection val set uses the `val` subset
        Args:
            batch_size: size of batch
            transforms: custom transforms
        """
        return DataLoader(
            self.testset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            drop_last=self.drop_last,
            pin_memory=self.pin_memory,
            collate_fn=self._collate_fn,
        )

    def _collate_fn(self, batch):
        return tuple(zip(*batch))