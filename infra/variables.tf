variable "aws_region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name prefix applied to resources"
  type        = string
  default     = "optify-video"
}

variable "vpc_cidr" {
  description = "CIDR block for the primary VPC"
  type        = string
  default     = "10.100.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = [
    "10.100.0.0/20",
    "10.100.16.0/20"
  ]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = [
    "10.100.32.0/20",
    "10.100.48.0/20"
  ]
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "msk_broker_instance_type" {
  description = "Instance type for MSK brokers"
  type        = string
  default     = "kafka.t3.small"
}

variable "eks_node_instance_types" {
  description = "Instance types for the EKS managed node group"
  type        = list(string)
  default     = ["t3.large"]
}

variable "eks_node_desired_size" {
  description = "Desired number of nodes in the managed node group"
  type        = number
  default     = 2
}

variable "enable_spot_nodes" {
  description = "Whether to use spot instances for EKS workers"
  type        = bool
  default     = true
}

variable "rtsp_source_ami" {
  description = "AMI ID for the RTSP EC2 host"
  type        = string
  default     = "ami-0cca134ec43cf708f" # Amazon Linux 2023 (ap-south-1)
}

variable "rtsp_source_instance_type" {
  description = "Instance type for the RTSP streaming host"
  type        = string
  default     = "t3.micro"
}

variable "rtsp_video_url" {
  description = "Public URL hosting the demo MP4, downloaded by user-data"
  type        = string
  default     = "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4"
}

variable "ssh_key_name" {
  description = "Optional SSH key pair name to attach to EC2 instances"
  type        = string
  default     = ""
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for annotated frames"
  type        = string
  default     = "optify-video-annotated"
}
