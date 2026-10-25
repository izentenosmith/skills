resource "azurerm_virtual_network" "hub" {
  name                = "vnet-hub"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
}

resource "azurerm_subnet" "nva" {
  name                 = "snet-nva"
  resource_group_name  = azurerm_resource_group.net.name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = ["10.0.1.0/27"]
}

resource "azurerm_subnet" "gateway" {
  name                 = "GatewaySubnet"
  resource_group_name  = azurerm_resource_group.net.name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = ["10.0.2.0/27"]
}

# Firewall appliance (third-party NVA). Spoke egress and hybrid traffic are routed through it.
resource "azurerm_network_interface" "nva" {
  name                  = "nic-fw-nva-01"
  location              = azurerm_resource_group.net.location
  resource_group_name   = azurerm_resource_group.net.name
  ip_forwarding_enabled = true

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.nva.id
    private_ip_address_allocation = "Static"
    private_ip_address            = "10.0.1.4"
  }
}

resource "azurerm_linux_virtual_machine" "nva" {
  name                  = "fw-nva-01"
  location              = azurerm_resource_group.net.location
  resource_group_name   = azurerm_resource_group.net.name
  size                  = "Standard_D4s_v5"
  admin_username        = "fwadmin"
  network_interface_ids = [azurerm_network_interface.nva.id]

  admin_ssh_key {
    username   = "fwadmin"
    public_key = file("${path.module}/keys/fwadmin.pub")
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }

  source_image_reference {
    publisher = "fortinet"
    offer     = "fortinet_fortigate-vm_v5"
    sku       = "fortinet_fg-vm_payg_2023"
    version   = "7.4.4"
  }
}

resource "azurerm_public_ip" "vgw" {
  name                = "pip-vgw-hub"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_virtual_network_gateway" "hub" {
  name                = "vgw-hub"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
  type                = "Vpn"
  vpn_type            = "RouteBased"
  sku                 = "VpnGw1"
  active_active       = false

  ip_configuration {
    name                 = "vgw-ipcfg"
    public_ip_address_id = azurerm_public_ip.vgw.id
    subnet_id            = azurerm_subnet.gateway.id
  }
}

resource "azurerm_local_network_gateway" "rotterdam" {
  name                = "lgw-rotterdam"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
  gateway_address     = "198.51.100.10"
  address_space       = ["10.40.0.0/16"]
}

resource "azurerm_virtual_network_gateway_connection" "rotterdam" {
  name                       = "cn-hub-rotterdam"
  location                   = azurerm_resource_group.net.location
  resource_group_name        = azurerm_resource_group.net.name
  type                       = "IPsec"
  virtual_network_gateway_id = azurerm_virtual_network_gateway.hub.id
  local_network_gateway_id   = azurerm_local_network_gateway.rotterdam.id
  shared_key                 = "Nw-Rtm-ipsec-7731xQ"
}

resource "azurerm_route_table" "gateway" {
  name                = "rt-gateway"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name

  route {
    name                   = "to-prod-via-nva"
    address_prefix         = "10.1.0.0/16"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = "10.0.1.4"
  }
}

resource "azurerm_subnet_route_table_association" "gateway" {
  subnet_id      = azurerm_subnet.gateway.id
  route_table_id = azurerm_route_table.gateway.id
}
