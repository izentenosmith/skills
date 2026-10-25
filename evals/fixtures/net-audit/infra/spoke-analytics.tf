resource "azurerm_virtual_network" "analytics" {
  name                = "vnet-analytics"
  address_space       = ["10.40.0.0/16"]
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
}

resource "azurerm_subnet" "analytics_jobs" {
  name                 = "snet-jobs"
  resource_group_name  = azurerm_resource_group.net.name
  virtual_network_name = azurerm_virtual_network.analytics.name
  address_prefixes     = ["10.40.8.0/24"]
}

resource "azurerm_subnet_route_table_association" "analytics_jobs" {
  subnet_id      = azurerm_subnet.analytics_jobs.id
  route_table_id = azurerm_route_table.prod.id
}

resource "azurerm_virtual_network_peering" "hub_to_analytics" {
  name                      = "peer-hub-analytics"
  resource_group_name       = azurerm_resource_group.net.name
  virtual_network_name      = azurerm_virtual_network.hub.name
  remote_virtual_network_id = azurerm_virtual_network.analytics.id
  allow_forwarded_traffic   = true
  allow_gateway_transit     = true
}

resource "azurerm_virtual_network_peering" "analytics_to_hub" {
  name                      = "peer-analytics-hub"
  resource_group_name       = azurerm_resource_group.net.name
  virtual_network_name      = azurerm_virtual_network.analytics.name
  remote_virtual_network_id = azurerm_virtual_network.hub.id
  allow_forwarded_traffic   = true
  use_remote_gateways       = true
}
