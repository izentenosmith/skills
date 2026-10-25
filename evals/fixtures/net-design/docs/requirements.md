# Fabrikam Payments — Azure network requirements

Collected by the platform team, 2026-10-20. Fabrikam is moving its card-acceptance platform from the
Utrecht data centre to Azure over the next two quarters.

## Business

- Merchant portal and public payment API, served to merchants and their customers over the internet.
- Card authorisation service: receives card data from the payment API and calls the acquirer. This is
  the **cardholder data environment** and is in scope for PCI DSS v4.0.
- Settlement batch: nightly, reads authorisations, writes settlement files to the acquirer over SFTP.
- Back-office reporting for finance, run by staff in Utrecht.

## Regions and availability

- Primary region **West Europe**, DR region **North Europe**. DR must be able to take over within
  4 hours; data is replicated continuously.
- The payment API and card authorisation must survive the loss of an availability zone.
- Growth: transaction volume is forecast to triple in three years; plan address space for it.

## Existing networks (must keep working; cannot be renumbered)

| Network | Range | Notes |
|---|---|---|
| Utrecht data centre | 10.0.0.0/12 | servers, storage, management; stays during and after migration |
| Branch offices (12) | 172.16.0.0/16 | SD-WAN, backhauled through Utrecht |
| Acquirer (Contoso Acquiring) | 10.64.0.0/16 and 192.168.100.0/24 | reached over a site-to-site VPN; their ranges, not ours |
| Staff VPN pool | 100.64.0.0/22 | remote staff, terminates in Utrecht |

Utrecht connects to Azure over ExpressRoute (primary) with a site-to-site VPN as backup.

## Platform

- Containers on AKS for the portal, payment API and authorisation service (Azure CNI Overlay is the
  team's preference). Azure Database for PostgreSQL Flexible Server for data.
- Platform team administers Azure from Utrecht and from the staff VPN pool.
- Auditors (QSA) will review the network design as part of the PCI assessment.

## Out of scope

Branch SD-WAN redesign; the acquirer's side of the VPN.
