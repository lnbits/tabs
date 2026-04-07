window.PageTabs = {
  template: '#page-tabs',
  delimiters: ['${', '}'],
  data() {
    return {
      tabsList: [],
      tabDetails: {},
      currencies: ['sats'],
      selected: [],
      filters: {
        status: null,
        includeArchived: false
      },
      statusOptions: [
        {label: 'Open', value: 'open'},
        {label: 'Suspended', value: 'suspended'},
        {label: 'Closed', value: 'closed'}
      ],
      limitTypeOptions: [
        {label: 'No Limit', value: 'none'},
        {label: 'Hard Limit', value: 'hard'}
      ],
      entryTypeOptions: [
        {label: 'Charge', value: 'charge'},
        {label: 'Credit', value: 'credit'},
        {label: 'Adjustment', value: 'adjustment'},
        {label: 'Note', value: 'note'}
      ],
      settlementMethodOptions: [
        {label: 'Lightning', value: 'lightning'},
        {label: 'Cash', value: 'cash'},
        {label: 'Card', value: 'card'},
        {label: 'Bank Transfer', value: 'bank_transfer'},
        {label: 'Other', value: 'other'},
        {label: 'Writeoff', value: 'writeoff'}
      ],
      entriesTable: {
        search: '',
        loading: false,
        columns: [
          {
            name: 'description',
            align: 'left',
            label: 'Description',
            field: 'description',
            sortable: false
          },
          {
            name: 'amount',
            align: 'left',
            label: 'Amount',
            field: row =>
              this.formatEntryAmount(
                row,
                this.tabDetails[row.tab_id]?.currency || 'sats'
              ),
            sortable: true
          },
          {
            name: 'entry_type',
            align: 'left',
            label: 'Type',
            field: 'entry_type',
            sortable: true
          },
          {
            name: 'source',
            align: 'left',
            label: 'Source',
            field: row =>
              `${row.source}${row.source_id ? ` (${row.source_id})` : ''}`,
            sortable: false
          },
          {
            name: 'created_at',
            align: 'left',
            label: 'Created',
            field: 'created_at',
            sortable: true,
            format: val => (val ? LNbits.utils.formatDateFrom(val) : '-')
          }
        ],
        pagination: {
          sortBy: 'created_at',
          rowsPerPage: 10,
          page: 1,
          descending: true,
          rowsNumber: 0
        }
      },
      tabsTable: {
        search: '',
        loading: false,
        columns: [
          {
            name: 'name',
            align: 'left',
            label: 'Name',
            field: 'name',
            sortable: true
          },
          {
            name: 'customer',
            align: 'left',
            label: 'Customer',
            field: row => row.customer_name || '',
            sortable: false
          },
          {
            name: 'reference',
            align: 'left',
            label: 'Reference',
            field: row => row.reference || '',
            sortable: false
          },
          {
            name: 'status',
            align: 'left',
            label: 'Status',
            field: 'status',
            sortable: true
          },
          {
            name: 'currency',
            align: 'left',
            label: 'Currency',
            field: 'currency',
            sortable: true
          },
          {
            name: 'balance',
            align: 'left',
            label: 'Balance',
            field: 'balance',
            sortable: true
          },
          {
            name: 'updated_at',
            align: 'left',
            label: 'Updated',
            field: 'updated_at',
            sortable: true,
            format: val => (val ? LNbits.utils.formatDateFrom(val) : '-')
          }
        ],
        pagination: {
          sortBy: 'updated_at',
          rowsPerPage: 10,
          page: 1,
          descending: true,
          rowsNumber: 0
        }
      },
      tabDialog: {
        show: false,
        data: {}
      },
      entryDialog: {
        show: false,
        tabId: null,
        currency: 'sats',
        title: 'New Entry',
        data: {}
      },
      settlementDialog: {
        show: false,
        tabId: null,
        currency: 'sats',
        balance: 0,
        data: {}
      }
    }
  },
  watch: {
    'tabsTable.search'() {
      this.getTabs()
    },
    'filters.status'() {
      this.getTabs()
    },
    'filters.includeArchived'() {
      this.getTabs()
    },
    selected() {
      if (this.selected.length === 1) {
        this.entriesTable.pagination.page = 1
        this.loadTabEntries(this.selected[0].id, {force: true})
      }
    }
  },
  methods: {
    ensureTabDetails(tabId) {
      const selectedTab = this.tabsList.find(tab => tab.id === tabId)
      if (!this.tabDetails[tabId]) {
        this.tabDetails[tabId] = {
          entries: [],
          settlements: [],
          currency: selectedTab?.currency || 'sats'
        }
      } else if (selectedTab?.currency) {
        this.tabDetails[tabId].currency = selectedTab.currency
      }
      return this.tabDetails[tabId]
    },
    emptyTabForm() {
      return {
        wallet: this.g?.user?.walletOptions?.[0]?.value || null,
        name: '',
        customer_name: '',
        reference: '',
        currency: 'sats',
        limit_type: 'none',
        limit_amount: null
      }
    },
    emptyEntryForm(entryType = 'charge') {
      return {
        entry_type: entryType,
        amount: null,
        description: '',
        source: '',
        source_id: '',
        idempotency_key: ''
      }
    },
    emptySettlementForm(balance = 0) {
      return {
        method: 'cash',
        amount: balance || null,
        reference: '',
        description: '',
        idempotency_key: ''
      }
    },
    amountStep(currency) {
      return currency === 'sats' ? '1' : '0.01'
    },
    amountMask(currency) {
      return currency === 'sats' ? '#' : '#.##'
    },
    normalizeAmount(currency, value) {
      if (value === null || value === undefined || value === '') return null
      return currency === 'sats' ? parseInt(value, 10) : parseFloat(value)
    },
    statusColor(status) {
      if (status === 'open') return 'positive'
      if (status === 'suspended') return 'warning'
      if (status === 'closed') return 'grey'
      return 'primary'
    },
    formatAmount(amount, currency) {
      if (currency === 'sats') {
        return `${Number(amount || 0).toLocaleString()} sats`
      }
      return LNbits.utils.formatCurrency(amount || 0, currency)
    },
    formatEntryAmount(entry, currency) {
      if (entry.entry_type === 'note') return 'No amount'
      const sign =
        entry.entry_type === 'charge'
          ? '+'
          : entry.entry_type === 'adjustment' && (entry.amount || 0) > 0
            ? '+'
            : ''
      return `${sign}${this.formatAmount(entry.amount || 0, currency)}`
    },
    async getTabs(props) {
      try {
        this.tabsTable.loading = true
        let params = LNbits.utils.prepareFilterQuery(this.tabsTable, props)
        if (this.filters.status) {
          params += `${params ? '&' : ''}status=${encodeURIComponent(this.filters.status)}`
        }
        params += `${params ? '&' : ''}is_archived=${this.filters.includeArchived}`
        const {data} = await LNbits.api.request(
          'GET',
          `/tabs/api/v1/tabs/paginated?${params}`
        )
        this.tabsList = data.data || []
        this.tabsTable.pagination.rowsNumber = data.total || 0
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.tabsTable.loading = false
      }
    },
    async loadTabEntries(tabId, options = {}) {
      const {force = false, props = null} = options
      const details = this.ensureTabDetails(tabId)
      if (details.entries.length && !force && !props) return

      try {
        this.entriesTable.loading = true
        const params = LNbits.utils.prepareFilterQuery(this.entriesTable, props)
        const {data} = await LNbits.api.request(
          'GET',
          `/tabs/api/v1/tabs/${tabId}/entries/paginated?${params}`
        )
        details.entries = data.data || []
        this.entriesTable.pagination.rowsNumber = data.total || 0
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.entriesTable.loading = false
      }
    },
    async requestTabEntries(props) {
      if (!this.selected.length) return
      await this.loadTabEntries(this.selected[0].id, {props})
    },
    async loadTabSettlements(tabId, force = false) {
      const details = this.ensureTabDetails(tabId)
      if (details.settlements.length && !force) return

      try {
        const {data} = await LNbits.api.request(
          'GET',
          `/tabs/api/v1/tabs/${tabId}/settlements?limit=10`
        )
        details.settlements = data || []
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    showCreateTabDialog() {
      this.tabDialog.data = this.emptyTabForm()
      this.tabDialog.show = true
    },
    showEditTabDialog(tab) {
      this.tabDialog.data = {
        id: tab.id,
        wallet: tab.wallet,
        name: tab.name,
        customer_name: tab.customer_name,
        reference: tab.reference,
        currency: tab.currency || 'sats',
        limit_type: tab.limit_type || 'none',
        limit_amount: tab.limit_amount
      }
      this.tabDialog.show = true
    },
    async saveTab() {
      try {
        const data = {...this.tabDialog.data}
        data.limit_amount =
          data.limit_type === 'hard'
            ? this.normalizeAmount(data.currency, data.limit_amount)
            : null
        const method = data.id ? 'PUT' : 'POST'
        const suffix = data.id ? `/${data.id}` : ''
        await LNbits.api.request(
          method,
          `/tabs/api/v1/tabs${suffix}`,
          null,
          data
        )
        this.tabDialog.show = false
        await this.getTabs()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    showEntryDialog(tab, entryType) {
      this.entryDialog.tabId = tab.id
      this.entryDialog.currency = tab.currency || 'sats'
      this.entryDialog.title = `Add ${entryType}`
      this.entryDialog.data = this.emptyEntryForm(entryType)
      this.entryDialog.show = true
    },
    async saveEntry() {
      try {
        const payload = {
          ...this.entryDialog.data,
          amount:
            this.entryDialog.data.entry_type === 'note'
              ? null
              : this.normalizeAmount(
                  this.entryDialog.currency,
                  this.entryDialog.data.amount
                )
        }
        await LNbits.api.request(
          'POST',
          `/tabs/api/v1/tabs/${this.entryDialog.tabId}/entries`,
          null,
          payload
        )
        this.entryDialog.show = false
        await this.getTabs()
        await this.loadTabEntries(this.entryDialog.tabId, {force: true})
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    showSettlementDialog(tab) {
      this.settlementDialog.tabId = tab.id
      this.settlementDialog.currency = tab.currency || 'sats'
      this.settlementDialog.balance = tab.balance || 0
      this.settlementDialog.data = this.emptySettlementForm(tab.balance || 0)
      this.settlementDialog.show = true
    },
    async saveSettlement() {
      try {
        const payload = {
          ...this.settlementDialog.data,
          amount: this.normalizeAmount(
            this.settlementDialog.currency,
            this.settlementDialog.data.amount
          )
        }
        const {data} = await LNbits.api.request(
          'POST',
          `/tabs/api/v1/tabs/${this.settlementDialog.tabId}/settlements`,
          null,
          payload
        )
        this.settlementDialog.show = false
        if (data.payment_request) {
          Quasar.Notify.create({
            type: 'info',
            message:
              'Lightning invoice created. Open the public page to complete payment.'
          })
        } else {
          Quasar.Notify.create({
            type: 'positive',
            message: 'Settlement recorded.'
          })
        }
        await this.getTabs()
        await Promise.all([
          this.loadTabEntries(this.settlementDialog.tabId, {force: true}),
          this.loadTabSettlements(this.settlementDialog.tabId, true)
        ])
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    async changeStatus(tab, status) {
      try {
        await LNbits.api.request(
          'POST',
          `/tabs/api/v1/tabs/${tab.id}/status`,
          null,
          {status}
        )
        await this.getTabs()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    async archiveTab(tab) {
      await LNbits.utils.confirmDialog('Archive this tab?').onOk(async () => {
        try {
          await LNbits.api.request(
            'POST',
            `/tabs/api/v1/tabs/${tab.id}/archive`
          )
          await this.getTabs()
        } catch (error) {
          LNbits.utils.notifyApiError(error)
        }
      })
    },
    async exportTabsCSV() {
      await LNbits.utils.exportCSV(
        this.tabsTable.columns,
        this.tabsList.map(tab => ({
          ...tab,
          balance: this.formatAmount(tab.balance, tab.currency)
        })),
        `tabs_${new Date().toISOString().slice(0, 10)}.csv`
      )
    }
  },
  async created() {
    if (g.allowedCurrencies && g.allowedCurrencies.length) {
      this.currencies = ['sats', ...g.allowedCurrencies]
    } else if (g.currencies && g.currencies.length) {
      this.currencies = ['sats', ...g.currencies]
    }
    await this.getTabs()
  }
}
