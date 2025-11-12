locals {
  tags = {
    Project     = var.project_name
    Environment = "assignment"
  }
}

module "network" {
  source                 = "./modules/network"
  project_name           = var.project_name
  vpc_cidr               = var.vpc_cidr
  availability_zones     = var.availability_zones
  public_subnet_cidrs    = var.public_subnet_cidrs
  private_subnet_cidrs   = var.private_subnet_cidrs
  enable_nat_gateway     = true
}

resource "aws_security_group" "shared_compute" {
  name        = "${var.project_name}-compute"
  description = "Shared security group for compute nodes"
  vpc_id      = module.network.vpc_id

  ingress {
    description = "Allow intra-VPC traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_security_group" "rtsp_public" {
  name        = "${var.project_name}-rtsp-public"
  description = "Ingress for RTSP streaming"
  vpc_id      = module.network.vpc_id

  ingress {
    description = "RTSP"
    from_port   = 8554
    to_port     = 8554
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

module "s3" {
  source       = "./modules/s3"
  bucket_name  = var.s3_bucket_name
  project_name = var.project_name
}

module "eks" {
  source             = "./modules/eks"
  project_name       = var.project_name
  vpc_id             = module.network.vpc_id
  subnet_ids         = module.network.private_subnet_ids
  node_instance_types = var.eks_node_instance_types
  node_desired_size   = var.eks_node_desired_size
  node_min_size       = 1
  node_max_size       = 5
  use_spot            = var.enable_spot_nodes
}

module "msk" {
  source                     = "./modules/msk"
  project_name               = var.project_name
  vpc_id                     = module.network.vpc_id
  subnet_ids                 = module.network.private_subnet_ids
  broker_instance_type       = var.msk_broker_instance_type
  broker_ebs_volume_size     = 20
  client_security_group_ids  = [aws_security_group.shared_compute.id]
}

module "rtsp" {
  source             = "./modules/ec2_rtsp"
  project_name       = var.project_name
  subnet_id          = module.network.public_subnet_ids[0]
  security_group_ids = [aws_security_group.rtsp_public.id]
  ami_id             = var.rtsp_source_ami
  instance_type      = var.rtsp_source_instance_type
  video_url          = var.rtsp_video_url
  ssh_key_name       = var.ssh_key_name
}
