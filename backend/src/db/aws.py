import logging
import sys
from src.logger import get_formatted_logger
import boto3
from pathlib import Path
from fastapi import Depends
from typing import Annotated
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_fixed, after_log, before_sleep_log
from src.config import global_config, Settings

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from urllib.parse import urlparse

logger = get_formatted_logger(__file__)


def get_aws_s3_client() -> "S3Client":
    return S3Client(
        aws_access_key_id=global_config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=global_config.AWS_SECRET_ACCESS_KEY,
        region_name=global_config.AWS_REGION_NAME,
        storage_type=global_config.AWS_STORAGE_TYPE,
        endpoint_url=global_config.AWS_ENDPOINT_URL,
    )


class S3Client:
    """
    AWS S3 client to interact with S3 service
    """

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_fixed(4),
        after=after_log(logger, logging.DEBUG),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
    )
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,
        storage_type: str,
        endpoint_url: str,
    ):
        """
        Initialize AWS S3 client

        Args:
            aws_access_key_id (str): AWS access key ID
            aws_secret_access_key (str): AWS secret access key
            region_name (str): AWS region name (e.g., 'us-east-1')
        """
        self.region_name = region_name
        self.storage_type = storage_type
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.client = boto3.client(
            service_name=storage_type,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            endpoint_url=endpoint_url,
        )
        self.test_connection()
        logger.info("S3Client initialized successfully!")

    @classmethod
    def from_setting(cls, global_config: Settings) -> "S3Client":
        return cls(
            aws_access_key_id=global_config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=global_config.AWS_SECRET_ACCESS_KEY,
            region_name=global_config.AWS_REGION_NAME,
            storage_type=global_config.AWS_STORAGE_TYPE,
            endpoint_url=global_config.AWS_ENDPOINT_URL,
        )

    def test_connection(self):
        """
        Test the connection with AWS S3 by listing buckets
        """
        try:
            self.client.list_buckets()
        except ClientError as e:
            raise ConnectionError(f"AWS S3 connection failed: {str(e)}")

    def check_bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if bucket exists in S3

        Args:
            bucket_name (str): Bucket name

        Returns:
            bool: True if bucket exists, False otherwise
        """
        try:
            self.client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False

    def create_bucket(self, bucket_name: str, region: str = None) -> None:
        """
        Create a bucket in S3 with an optional region

        Args:
            bucket_name (str): Bucket name
            region (str): AWS region (e.g., 'ap-southeast-1'). Defaults to instance region if None.
        """
        if region is None:
            region = self.region_name

        try:
            # Set the LocationConstraint only if the region is not 'us-east-1'
            if region == "us-east-1":
                self.client.create_bucket(Bucket=bucket_name)
            else:
                self.client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
            logger.info(
                f"Bucket {bucket_name} created successfully in region {region}!"
            )
        except ClientError as e:
            if "BucketAlreadyOwnedByYou" not in str(e):
                logger.error(f"Failed to create bucket: {e}")
                raise

    @retry(stop=stop_after_attempt(3))
    def upload_file(
        self, bucket_name: str, object_name: str, file_path: str | Path
    ) -> None:
        """
        Upload file to S3

        Args:
            bucket_name (str): Bucket name
            object_name (str): Object name to save in S3
            file_path (str | Path): Local file path to be uploaded
        """
        file_path = str(file_path)

        if self.check_bucket_exists(bucket_name) is False:
            logger.debug(f"Bucket {bucket_name} does not exist. Creating bucket...")
            self.create_bucket(bucket_name)
            # Generate date-based path in format yy/mm/dd
        try:
            self.client.upload_file(
                Filename=file_path,
                Bucket=bucket_name,
                Key=object_name,
                # ExtraArgs={'ACL':'public-read'}
            )
            logger.info(f"Uploaded: {file_path} --> {bucket_name}/{object_name}")
            return f"https://{bucket_name}.{self.storage_type}.{self.region_name}.amazonaws.com/{object_name}"
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise e

    def download_file(self, file_url: str, file_path_to_save: str):
        """
        Download file from S3

        Args:
            file_url (str): Object name to download
            file_path_to_save (str): File path to save
        """
        try:
            parsed = urlparse(file_url)

            # Extract bucket name from hostname
            hostname_parts = parsed.netloc.split(".")
            bucket_name = hostname_parts[0]
            if not self.check_bucket_exists(bucket_name):
                logger.warning(f"Bucket {bucket_name} does not exist. Do nothing...")
                return
            # Extract object key from path
            object_name = parsed.path.lstrip("/")

            self.client.download_file(
                Bucket=bucket_name, Key=object_name, Filename=file_path_to_save
            )
            logger.info(
                f"Downloaded: {bucket_name}/{object_name} --> {file_path_to_save}"
            )
        except ClientError as e:
            logger.error(f"Download failed: {str(e)}")
            raise

    def remove_file(self, object_name: str) -> None:
        """
        Remove file from S3

        Args:
            object_name (str): Object name to remove
        """

        try:
            parsed = urlparse(object_name)

            # Extract bucket name from hostname
            hostname_parts = parsed.netloc.split(".")
            bucket_name = hostname_parts[0]
            if not self.check_bucket_exists(bucket_name):
                logger.warning(f"Bucket {bucket_name} does not exist. Do nothing...")
                return
            # Extract object key from path
            object_name = parsed.path.lstrip("/")
            self.client.delete_object(
                Bucket=bucket_name,
                Key=object_name,
            )
            logger.debug(f"Removed from S3: {bucket_name}/{object_name}")
        except ClientError as e:
            logger.error(f"Remove failed: {str(e)}")
            raise

    def remove_bucket(self, bucket_name: str) -> None:
        """
        Remove bucket from S3

        Args:
            bucket_name (str): Bucket name
        """
        if not self.check_bucket_exists(bucket_name):
            logger.warning(f"Bucket {bucket_name} does not exist. Cannot remove...")
            return

        try:
            # List and delete all objects in the bucket
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        self.client.delete_object(Bucket=bucket_name, Key=obj["Key"])

            # Delete the bucket itself
            self.client.delete_bucket(Bucket=bucket_name)
            logger.info(f"Removed bucket: {bucket_name}")
        except ClientError as e:
            logger.error(f"Bucket removal failed: {str(e)}")
            raise
