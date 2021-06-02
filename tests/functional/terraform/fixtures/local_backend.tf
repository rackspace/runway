terraform {
  backend "local" {
    path = "local_backend"
  }
}

resource "null_resource" "test" {
  provisioner "local-exec" {
    command = "echo 'Hello World'"
  }
}
