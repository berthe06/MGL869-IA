import datetime
import pytz
import logging

from django.core.management.base import BaseCommand
from images.models import Image, CATEGORIES, PROCESSES
from django.conf import settings

import cv2
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from pickle import dump

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=settings.BASE_DIR / "model/repository/training_sklearn.log",
    level=logging.INFO,
    format="%(message)s",
)


class Command(BaseCommand):
    help = "Train the model"

    def add_arguments(self, parser):
        parser.add_argument("--model_name", action="store", dest="model_name", type=str)

    def handle(self, *args, **options):
        # Load data and preprocess.
        # ------------------------------
        # Preprocessing 1 - Resize - The CNN requires the images to be in the same size.
        # Ppeprocessing 2 - Normalize - The CNN works better with values between 0 and 1.
        # Returns a DataFrame with the images and their labels.
        def read_imgs(
            process: PROCESSES, img_width: int, img_height: int
        ) -> pd.DataFrame:
            data = []
            labels = []
            images = Image.objects.filter(process=process)
            for image in images:
                img = cv2.imread(image.src.path)
                img = cv2.resize(img, (img_width, img_height))  # Resize
                img = img / 255.0  # Normalize
                data.append(img)
                class_name = CATEGORIES(image.category).label
                labels.append(class_name)
            # Convert labels to integers to use with the CNN.
            le = LabelEncoder()
            labels = le.fit_transform(labels)
            df = pd.DataFrame(list(zip(data, labels)), columns=["image", "class"])
            return df

        img_width = settings.IMAGE_WIDTH
        img_height = settings.IMAGE_HEIGHT

        def load_train_data():
            train_imgs = read_imgs(PROCESSES.TRAINING, img_width, img_height)
            return train_imgs

        def load_valid_data():
            valid_imgs = read_imgs(PROCESSES.VALIDATION, img_width, img_height)
            return valid_imgs

        train_data = load_train_data()
        valid_data = load_valid_data()

        # Data analysis
        # ------------------------------
        logger.info("-------------------")
        logger.info("Image size:")
        logger.info("-------------------")
        logger.info(f"{img_width} x {img_height}")
        logger.info("-------------------")
        logger.info("Data shape:")
        logger.info("-------------------")
        logger.info(f"{len(train_data['image'])} x {img_width*img_height*3}")
        logger.info("-------------------")

        # logger.info train data first 5 rows
        logger.info("Train data first 5 rows:")
        logger.info("-------------------")
        logger.info(train_data.head())
        logger.info("-------------------")

        # logger.info validation data first 5 rows
        logger.info("Validation data first 5 rows:")
        logger.info("-------------------")

        # Quantify the data
        logger.info("Train data class distribution:")
        logger.info("-------------------")
        logger.info(train_data["class"].value_counts())
        logger.info("-------------------")

        logger.info("Validation data class distribution:")
        logger.info("-------------------")
        logger.info(valid_data["class"].value_counts())
        logger.info("-------------------")

        # LinearSVC model
        clf = make_pipeline(StandardScaler(), LinearSVC(random_state=0, tol=1e-5))

        # Convert the 'image' column to a NumPy array
        train_images = np.stack(train_data["image"].values)
        train_images = np.reshape(train_images, (len(train_images), img_width*img_height*3))
        train_labels = train_data["class"].values

        valid_images = np.stack(valid_data["image"].values)
        valid_images = np.reshape(valid_images, (len(valid_images), img_width*img_height*3))
        valid_labels = valid_data["class"].values

        a = datetime.datetime.now(pytz.timezone("America/Montreal"))
        logger.info(a)

        # Fit the model
        clf.fit(train_images, train_labels)

        b = datetime.datetime.now(pytz.timezone("America/Montreal"))
        logger.info(b)

        logger.info(f"Training time: {b - a}")

        # Evaluate the model
        score = clf.score(valid_images, valid_labels)

        logger.info("LinearSVC Score:")
        logger.info("-------------------")
        logger.info(score)
        logger.info("-------------------")
        logger.info(f"Image size: {img_width} x {img_height}")
        logger.info("-------------------")

        # # Save the model in .pkl format
        model_name = options.get("model_name")
        # model.save(settings.BASE_DIR / "model/repository" / f"{model_name}.keras")
        with open(settings.BASE_DIR / "model/repository" / f"{model_name}.pkl", "wb") as f:
            dump(clf, f, protocol=5)

        """
        from pickle import load
        with open("filename.pkl", "rb") as f:
            clf = load(f)
        """