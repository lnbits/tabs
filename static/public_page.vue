<template id="page-tabs-public">
  <div class="row q-col-gutter-md justify-center">
    <div class="col-12 col-md-6 col-lg-5 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <div class="text-overline">Customer Settlement</div>
          <div class="text-h4" v-text="tab.name || 'Tab'"></div>
          <div
            v-if="tab.customer_name"
            class="text-subtitle1 q-mt-xs"
            v-text="tab.customer_name"
          ></div>
        </q-card-section>
        <q-card-section>
          <div class="text-subtitle2">Entries</div>
          <q-list dense>
            <q-item v-for="entry in tab.entries" :key="entry.id">
              <q-item-section>
                <q-item-label
                  v-text="entry.description || 'Entry'"
                ></q-item-label>
                <q-item-label caption v-if="entry.quantity != null">
                  Quantity: {{ entry.quantity }} {{ entry.unit_label || '' }}
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-item-label
                  v-text="formatAmount(entry.amount, tab.currency)"
                ></q-item-label>
              </q-item-section>
            </q-item>
            <q-item v-if="!tab.entries || tab.entries.length === 0">
              <q-item-section class="text-center">
                <q-item-label caption>No entries found.</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-section class="q-pt-none">
          Outstanding balance:
          <span
            class="text-weight-medium"
            v-text="formatAmount(tab.balance || 0, tab.currency)"
          ></span>
        </q-card-section>
        <q-card-actions
          v-if="tab.status !== 'closed' && (tab.balance || 0) > 0"
          align="right"
          class="q-pa-md"
        >
          <q-btn unelevated color="primary" @click="openFormDialog">
            Pay Tab
          </q-btn>
        </q-card-actions>
        <q-card-section
          v-else-if="tab.status === 'closed' || (tab.balance || 0) <= 0"
          class="q-pt-none"
        >
          <q-banner dense rounded class="text-positive">
            This tab is settled.
          </q-banner>
        </q-card-section>
      </q-card>

      <q-card v-if="invoicePaid">
        <q-card-section class="text-center">
          <q-icon name="check_circle" color="positive" size="64px"></q-icon>
          <div class="text-h6 q-mt-sm">Payment Received</div>
          <div class="text-body2">The tab balance has been refreshed.</div>
        </q-card-section>
      </q-card>
    </div>

    <div class="col-12 col-md-4 col-lg-3 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <div class="text-subtitle2">Tab Summary</div>
        </q-card-section>
        <q-list separator>
          <q-item>
            <q-item-section>
              <q-item-label caption>Customer</q-item-label>
              <q-item-label v-text="tab.customer_name || '-'"></q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label caption>Status</q-item-label>
              <q-item-label v-text="tab.status || '-'"></q-item-label>
            </q-item-section>
          </q-item>
          <q-item>
            <q-item-section>
              <q-item-label caption>Currency</q-item-label>
              <q-item-label v-text="tab.currency || '-'"></q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </div>

    <q-dialog v-model="formDialog.show" position="top" @hide="closeFormDialog">
      <q-card class="q-pa-lg q-pt-xl lnbits__dialog-card">
        <q-form @submit="submitSettlement" class="q-gutter-md">
          <div class="text-h5">Create Payment</div>

          <q-input
            filled
            dense
            v-model.number="formDialog.data.amount"
            type="number"
            :label="'Amount (' + (tab.currency || 'sats') + ')'"
            :step="amountStep(tab.currency || 'sats')"
            :mask="amountMask(tab.currency || 'sats')"
            fill-mask="0"
            reverse-fill-mask
            :rules="[val => validAmount(val) || 'Enter a valid amount']"
          >
            <template v-slot:append>
              <span
                style="font-size: 12px"
                v-text="tab.currency || 'sats'"
              ></span>
            </template>
          </q-input>

          <q-input
            filled
            dense
            v-model.trim="formDialog.data.reference"
            label="Reference"
          ></q-input>

          <div class="row q-mt-lg">
            <q-btn
              unelevated
              color="primary"
              type="submit"
              :disable="formDialog.data.amount == null"
            >
              Generate Invoice
            </q-btn>
            <q-btn v-close-popup flat color="grey" class="q-ml-auto">
              Cancel
            </q-btn>
          </div>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog
      v-model="qrCodeDialog.show"
      position="top"
      @hide="closeQrCodeDialog"
    >
      <q-card class="q-pa-lg q-pt-xl lnbits__dialog-card text-center">
        <div class="text-subtitle1 q-mb-md">
          <span
            v-text="formatAmount(qrCodeDialog.data.amount, tab.currency)"
          ></span>
        </div>
        <a
          v-if="qrCodeDialog.data.payment_request"
          class="text-secondary"
          :href="'lightning:' + qrCodeDialog.data.payment_request"
        >
          <lnbits-qrcode
            :value="'lightning:' + qrCodeDialog.data.payment_request"
          ></lnbits-qrcode>
        </a>
        <div class="q-mt-md">
          <q-btn outline color="grey" @click="copyPaymentRequest">
            Copy Invoice
          </q-btn>
        </div>
      </q-card>
    </q-dialog>
  </div>
</template>
