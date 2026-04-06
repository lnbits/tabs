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
    validAmount(value) {
      return value !== null && value !== undefined && value !== '' && Number(value) > 0
    },
    formatAmount(amount, currency) {
      if (currency === 'sats') {
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
        this.tab = data || {}
        if (!this.formDialog.data.amount) {
          this.formDialog.data.amount = this.tab.balance || null
        }
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
        this.qrCodeDialog.data = {
          amount: data.settlement?.amount || payload.amount,
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
  }
}
