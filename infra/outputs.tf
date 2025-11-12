output "vpc_id" {
  value = module.network.vpc_id
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "msk_bootstrap_brokers" {
  value = module.msk.bootstrap_brokers_tls
}

output "s3_bucket_name" {
  value = module.s3.bucket_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "eks_cluster_ca" {
  value = module.eks.cluster_certificate_authority_data
}

output "rtsp_public_ip" {
  value = module.rtsp.public_ip
}
