window.PageTabsPublic = {
  template: '#page-tabs-public',
  data() {
    return {
      tabId: null,
      tab: {},
      paymentHash: '',
      invoicePaid: false,
      formDialog: {
        show: false,
        data: {
          amount: null,
          reference: ''
        }
      },
      qrCodeDialog: {
        show: false,
        data: {
          amount: null,
          payment_request: ''
        },
        dismissMsg: null
      }
    }
  },
  methods: {
    isSatsCurrency(currency) {
      return (currency || 'sats').toLowerCase() === 'sats'
    },
    amountScale(currency) {
      if (this.isSatsCurrency(currency)) return 1
      try {
        const digits = new Intl.NumberFormat(window.i18n.global.locale, {
          style: 'currency',
          currency: (currency || '').toUpperCase()
        }).resolvedOptions().maximumFractionDigits
        return 10 ** digits
      } catch {
        return 100
      }
    },
    mapPublicTab(tab) {
      const currency = tab?.currency || 'sats'
      return {
        ...(tab || {}),
        currency,
        balance: this.normalizeAmount(currency, tab?.balance) || 0
      }
    },
    mapPublicEntries(entries, currency) {
      return (entries || []).map(entry => ({
        ...entry,
        amount: this.normalizeAmount(currency, entry?.amount) ?? 0
      }))
    },
    amountStep(currency) {
      return this.isSatsCurrency(currency) ? '1' : '0.01'
    },
    amountMask(currency) {
      return this.isSatsCurrency(currency) ? '#' : '#.##'
    },
    normalizeAmount(currency, value) {
      if (value === null || value === undefined || value === '') return null
      const parsed = Number(value)
      if (Number.isNaN(parsed)) return null
      if (this.isSatsCurrency(currency)) return Math.round(parsed)
      const scale = this.amountScale(currency)
      return Math.round(parsed * scale) / scale
    },
    validAmount(value) {
      return (
        value !== null &&
        value !== undefined &&
        value !== '' &&
        Number(value) > 0
      )
    },
    formatAmount(amount, currency) {
      if (this.isSatsCurrency(currency)) {
        return `${Number(amount || 0).toLocaleString()} sats`
      }
      return LNbits.utils.formatCurrency(amount || 0, currency)
    },
    async fetchTab() {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          `/tabs/api/v1/public/tabs/${this.tabId}`
        )
        this.tab = this.mapPublicTab(data)
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    async fetchEntries() {
      try {
        const {data} = await LNbits.api.request(
          'GET',
          `/tabs/api/v1/public/tabs/${this.tabId}/entries`
        )
        this.tab.entries = this.mapPublicEntries(data, this.tab.currency || 'sats')
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    openFormDialog() {
      this.formDialog.show = true
      this.formDialog.data.amount = this.tab.balance || null
      this.formDialog.data.reference = ''
    },
    closeFormDialog() {
      this.formDialog.show = false
    },
    closeQrCodeDialog() {
      this.qrCodeDialog.show = false
      if (this.qrCodeDialog.dismissMsg) {
        this.qrCodeDialog.dismissMsg()
        this.qrCodeDialog.dismissMsg = null
      }
    },
    async submitSettlement() {
      try {
        const payload = {
          amount: this.normalizeAmount(
            this.tab.currency || 'sats',
            this.formDialog.data.amount
          ),
          reference: this.formDialog.data.reference
        }
        const {data} = await LNbits.api.request(
          'POST',
          `/tabs/api/v1/public/tabs/${this.tabId}/settlements`,
          null,
          payload
        )

        if (!data.payment_request) {
          throw new Error('No payment request received')
        }

        this.formDialog.show = false
        this.invoicePaid = false
        this.paymentHash = data.settlement?.payment_hash || ''
        const settlementAmount = this.normalizeAmount(
          this.tab.currency || 'sats',
          data.settlement?.amount
        )
        this.qrCodeDialog.data = {
          amount: settlementAmount ?? payload.amount,
          payment_request: data.payment_request
        }
        this.qrCodeDialog.show = true

        if (this.paymentHash) {
          this.subscribeToPaymentWs(this.paymentHash)
        }

        this.qrCodeDialog.dismissMsg = Quasar.Notify.create({
          timeout: 0,
          message: 'Waiting for payment...'
        })
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },
    subscribeToPaymentWs(paymentHash) {
      const url = new URL(window.location)
      url.protocol = url.protocol === 'https:' ? 'wss' : 'ws'
      url.pathname = `/api/v1/ws/${paymentHash}`
      const ws = new WebSocket(url)
      ws.addEventListener('message', async ({data}) => {
        const resp = JSON.parse(data)
        if (!resp.pending || resp.paid) {
          Quasar.Notify.create({
            type: 'positive',
            message: 'Invoice Paid!'
          })
          this.invoicePaid = true
          this.closeQrCodeDialog()
          await this.fetchTab()
          await this.fetchEntries()
          ws.close()
        }
      })
    },
    copyPaymentRequest() {
      if (!this.qrCodeDialog.data.payment_request) return
      LNbits.utils.copyText(
        'lightning:' + this.qrCodeDialog.data.payment_request,
        'Invoice copied'
      )
    }
  },
  async created() {
    this.tabId = this.$route.params.id
    await this.fetchTab()
    await this.fetchEntries()
  }
}
