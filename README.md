<a href="https://lnbits.com" target="_blank" rel="noopener noreferrer">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://i.imgur.com/QE6SIrs.png">
    <img src="https://i.imgur.com/fyKPgVT.png" alt="LNbits" style="width:280px">
  </picture>
</a>

[![License: MIT](https://img.shields.io/badge/License-MIT-success?logo=open-source-initiative&logoColor=white)](./LICENSE)
[![Built for LNbits](https://img.shields.io/badge/Built%20for-LNbits-4D4DFF?logo=lightning&logoColor=white)](https://github.com/lnbits/lnbits)
[![tip-hero](https://img.shields.io/badge/TipJar-LNBits%20Hero-9b5cff?labelColor=6b7280&logo=lightning&logoColor=white)](https://demo.lnbits.com/tipjar/DwaUiE4kBX6mUW6pj3X5Kg)
[![Explore LNbits Extensions](https://img.shields.io/badge/Explore-LNbits%20Extensions-10B981?logo=puzzle-piece&logoColor=white&labelColor=065F46)](https://extensions.lnbits.com/)

# Tabs — _[LNbits](https://lnbits.com) extension_

**A reusable merchant ledger for open balances that can be charged incrementally and settled later.**
Create named tabs for customers, tables, teams, events, or internal accounts, then add charges, credits, notes, and settlements over time.

Tabs is intentionally generic: other LNbits extensions can post entries into Tabs, while Tabs owns the tab lifecycle, balance rules, audit history, and settlement flow.

---

### Quick Links

- [Features](#features)
- [Overview](#overview)
- [Usage](#usage)
- [Creating Tabs](#creating-tabs)
- [Adding Activity](#adding-activity)
- [Settlements](#settlements)
- [TPoS Integration](#tpos-integration)
- [Powered by LNbits](#powered-by-lnbits)

## Features

- **Open tab management** — create, edit, suspend, close, archive, and delete empty tabs
- **Running balances** — charge, credit, adjustment, settlement, and note entries
- **Deferred settlement** — settle partially or fully after the service session
- **Lightning settlement** — create a standard LNbits invoice and complete the settlement when paid
- **Manual settlement** — record cash, card, bank transfer, other, or write-off settlement methods
- **Public tab view** — share a tab page where a payer can inspect and settle the balance
- **CSV export** — export tab data from the management UI
- **TPoS ready** — supports the deferred “Book to Tab” point-of-sale workflow

## Overview

Tabs keeps a merchant-controlled list of open balances. It records what a customer, group, event, or account owes, then lets the merchant clear that balance through a Lightning invoice or a manual settlement record.

Common use cases:

- Bar, cafe, or canteen tabs
- Event and festival organizer tabs
- Office kitchen or staff meal accounts
- Corporate house accounts
- Coworking, hospitality, or service-session billing

## Usage

1. **Enable** the Tabs extension.

2. **Create** a new tab.

   Choose the wallet that owns the tab, add a name, optional customer/reference details, currency, and an optional hard limit.

   <img src="https://raw.githubusercontent.com/lnbits/tabs/main/static/image/1.png" alt="Tabs management screen" width="720">

3. **Add entries** as activity happens.

   Charges increase the balance. Credits and settlements reduce it. Notes preserve context without changing the amount due.

4. **Settle** part or all of the balance.

   Use a Lightning invoice for automatic payment tracking, or record a manual method such as cash, card, bank transfer, other, or write-off.

5. **Close or archive** settled tabs.

   Tabs can only be closed when their balance is zero. Tabs with financial history should be archived instead of deleted.

## Creating Tabs

Create a tab for a customer, table, team, event, or internal account.

You can set:

- **Wallet** — the wallet that owns the tab
- **Name** — the visible tab name
- **Customer** — optional customer or group name
- **Reference** — optional room, table, event, invoice, or account reference
- **Currency** — sats or supported fiat currency
- **Limit type** — no limit or hard limit
- **Limit amount** — maximum balance when a hard limit is active

Use the tabs list to search, filter by status, open public pages, export CSV, and select a tab to view its activity.

## Adding Activity

Every tab has a running activity history. Add entries as purchases, corrections, or notes happen.

Supported entry types:

- **Charge** — increases the tab balance
- **Credit** — reduces the tab balance
- **Adjustment** — increases or reduces the tab balance
- **Settlement** — reduces the balance after payment or manual clearing
- **Note** — records context without changing the balance

Suspended tabs cannot receive new charges. Closed and archived tabs are kept for history.

## Settlements

Tabs supports both Lightning and manual settlement flows.

### Lightning Settlement

1. The merchant starts a settlement for the full or partial balance.
2. Tabs creates a normal LN invoice from the tab wallet.
3. A pending settlement is stored with the invoice data.
4. When the invoice is paid, Tabs marks the settlement complete.
5. A settlement ledger entry is added and the tab balance is updated.
6. If the balance reaches zero, the tab may be closed.

### Manual Settlement

Manual methods are completed immediately and still create auditable settlement history.

Supported manual methods:

- `cash`
- `card`
- `bank_transfer`
- `other`
- `writeoff`

## Public Tab Page

Each tab can expose a public tab page at:

```text
/tabs/{tab_id}
```

The public page lets someone inspect and pay an outstanding tab without giving them merchant management access.

## TPoS Integration

Tabs is designed so TPoS can stay focused on point-of-sale interaction.

Intended flow:

1. The merchant can create a tab in TPoS.
2. The merchant chooses **Add to Tab**.
3. TPoS loads eligible tabs from Tabs.
4. The merchant selects a tab.
5. TPoS posts one summarized charge entry with amount, items, tax, and source details.
6. Tabs records the charge and returns the updated tab state.
7. TPoS clears the cart and confirms the booking.

Tabs owns the balance and history, so the same tab can also be managed from the Tabs extension after TPoS adds a charge.

## Powered by LNbits

LNbits empowers developers and merchants with modular, open-source tools for building Bitcoin-based systems — fast, free, and extendable.

[![Visit LNbits Shop](https://img.shields.io/badge/Visit-LNbits%20Shop-7C3AED?logo=shopping-cart&logoColor=white&labelColor=5B21B6)](https://shop.lnbits.com/)
[![Try myLNbits SaaS](https://img.shields.io/badge/Try-myLNbits%20SaaS-2563EB?logo=lightning&logoColor=white&labelColor=1E40AF)](https://my.lnbits.com/login)
[![Read LNbits News](https://img.shields.io/badge/Read-LNbits%20News-F97316?logo=rss&logoColor=white&labelColor=C2410C)](https://news.lnbits.com/)
[![Explore LNbits Extensions](https://img.shields.io/badge/Explore-LNbits%20Extensions-10B981?logo=puzzle-piece&logoColor=white&labelColor=065F46)](https://extensions.lnbits.com/) [![tip-hero](https://img.shields.io/badge/TipJar-LNBits%20Hero-9b5cff?labelColor=7c3aed&logo=lightning&logoColor=white)](https://demo.lnbits.com/tipjar/DwaUiE4kBX6mUW6pj3X5Kg)
