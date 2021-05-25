terraform {
  backend "s3" {}
}

resource "null_resource" "test" {
  provisioner "local-exec" {
    command = "echo 'Hello World'"
  }
}
