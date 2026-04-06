<template id="page-tabs">
  <q-page class="row q-col-gutter-md">
    <div class="col-12 col-md-8 col-lg-7 q-gutter-y-md">
      <q-card>
        <q-card-section class="row items-center no-wrap">
          <div class="col">
            <h5 class="text-subtitle1 q-my-none">Tabs</h5>
            <div class="text-caption">Reusable merchant ledger with deferred settlement.</div>
          </div>
          <div class="col-auto row q-gutter-sm">
            <q-btn flat color="grey" icon="file_download" @click="exportTabsCSV">
              Export CSV
            </q-btn>
            <q-btn unelevated color="primary" @click="showCreateTabDialog">
              New Tab
            </q-btn>
          </div>
        </q-card-section>
      </q-card>

      <q-card>
        <q-card-section>
          <div class="row q-col-gutter-md q-mb-md">
            <div class="col-12 col-md-5">
              <q-input v-model="tabsTable.search" dense filled label="Search tabs">
                <template v-slot:prepend>
                  <q-icon name="search"></q-icon>
                </template>
                <template v-slot:append>
                  <q-icon
                    v-if="tabsTable.search"
                    name="close"
                    class="cursor-pointer"
                    @click="tabsTable.search = ''"
                  ></q-icon>
                </template>
              </q-input>
            </div>
            <div class="col-12 col-sm-6 col-md-3">
              <q-select
                v-model="filters.status"
                dense
                filled
                emit-value
                map-options
                clearable
                :options="statusOptions"
                label="Status"
              ></q-select>
            </div>
            <div class="col-12 col-sm-6 col-md-4 flex items-center">
              <q-toggle v-model="filters.includeArchived" label="Show archived tabs"></q-toggle>
            </div>
          </div>

          <q-table
            dense
            flat
            row-key="id"
            :rows="tabsList"
            :columns="tabsTable.columns"
            v-model:pagination="tabsTable.pagination"
            :loading="tabsTable.loading"
            @request="getTabs"
          >
            <template v-slot:header="props">
              <q-tr :props="props">
                <q-th auto-width></q-th>
                <q-th auto-width></q-th>
                <q-th v-for="col in props.cols" :key="col.name" :props="props" v-text="col.label"></q-th>
              </q-tr>
            </template>

            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td auto-width>
                  <q-btn
                    size="sm"
                    color="accent"
                    round
                    dense
                    :icon="props.expand ? 'expand_less' : 'expand_more'"
                    @click.stop="toggleRow(props)"
                  ></q-btn>
                </q-td>
                <q-td auto-width>
                  <div class="row no-wrap q-gutter-xs">
                    <q-btn
                      flat
                      dense
                      size="xs"
                      icon="launch"
                      color="primary"
                      type="a"
                      :href="'/tabs/' + props.row.id"
                      target="_blank"
                      @click.stop
                    >
                      <q-tooltip>Open public page</q-tooltip>
                    </q-btn>
                    <q-btn
                      flat
                      dense
                      size="xs"
                      icon="edit"
                      color="blue"
                      @click.stop="showEditTabDialog(props.row)"
                    >
                      <q-tooltip>Edit tab</q-tooltip>
                    </q-btn>
                    <q-btn
                      flat
                      dense
                      size="xs"
                      icon="post_add"
                      color="positive"
                      @click.stop="showEntryDialog(props.row, 'charge')"
                    >
                      <q-tooltip>Add charge</q-tooltip>
                    </q-btn>
                    <q-btn
                      flat
                      dense
                      size="xs"
                      icon="payments"
                      color="orange"
                      @click.stop="showSettlementDialog(props.row)"
                    >
                      <q-tooltip>Settle tab</q-tooltip>
                    </q-btn>
                  </div>
                </q-td>
                <q-td key="name" :props="props" v-text="props.row.name"></q-td>
                <q-td key="customer" :props="props" v-text="props.row.customer_name || '-'"></q-td>
                <q-td key="reference" :props="props" v-text="props.row.reference || '-'"></q-td>
                <q-td key="status" :props="props">
                  <q-badge :color="statusColor(props.row.status)">
                    <span v-text="props.row.status"></span>
                  </q-badge>
                </q-td>
                <q-td key="currency" :props="props" v-text="props.row.currency"></q-td>
                <q-td key="balance" :props="props" v-text="formatAmount(props.row.balance, props.row.currency)"></q-td>
                <q-td key="updated_at" :props="props" v-text="dateFromNow(props.row.updated_at)"></q-td>
              </q-tr>
              <q-tr v-show="props.expand" :props="props">
                <q-td colspan="100%">
                  <div class="row q-col-gutter-lg q-py-md">
                    <div class="col-12 col-lg-4 q-gutter-y-md">
                      <q-card bordered>
                        <q-card-section class="q-gutter-y-sm">
                          <div class="text-subtitle2">Tab Details</div>
                          <div class="text-caption">
                            Wallet
                            <span class="text-weight-medium" v-text="props.row.wallet"></span>
                          </div>
                          <div class="text-caption">
                            Currency
                            <span class="text-weight-medium" v-text="props.row.currency"></span>
                          </div>
                          <div class="text-caption">
                            Limit
                            <span class="text-weight-medium" v-text="formatLimit(props.row)"></span>
                          </div>
                          <div class="text-caption">
                            Public page
                            <a :href="'/tabs/' + props.row.id" target="_blank">
                              <span v-text="'/tabs/' + props.row.id"></span>
                            </a>
                          </div>
                        </q-card-section>
                        <q-separator></q-separator>
                        <q-card-section class="row q-col-gutter-sm">
                          <div class="col-12">
                            <q-btn unelevated color="primary" class="full-width" @click="showEntryDialog(props.row, 'charge')">
                              Add Charge
                            </q-btn>
                          </div>
                          <div class="col-4">
                            <q-btn outline color="primary" class="full-width" @click="showEntryDialog(props.row, 'credit')">
                              Credit
                            </q-btn>
                          </div>
                          <div class="col-4">
                            <q-btn outline color="primary" class="full-width" @click="showEntryDialog(props.row, 'adjustment')">
                              Adjust
                            </q-btn>
                          </div>
                          <div class="col-4">
                            <q-btn outline color="primary" class="full-width" @click="showEntryDialog(props.row, 'note')">
                              Note
                            </q-btn>
                          </div>
                          <div class="col-12">
                            <q-btn outline color="orange" class="full-width" @click="showSettlementDialog(props.row)">
                              Settle
                            </q-btn>
                          </div>
                        </q-card-section>
                        <q-separator></q-separator>
                        <q-card-section class="row q-col-gutter-sm">
                          <div class="col-6">
                            <q-btn flat class="full-width" @click="changeStatus(props.row, 'open')" :disable="props.row.status === 'open'">
                              Open
                            </q-btn>
                          </div>
                          <div class="col-6">
                            <q-btn flat class="full-width" @click="changeStatus(props.row, 'suspended')" :disable="props.row.status === 'suspended'">
                              Suspend
                            </q-btn>
                          </div>
                          <div class="col-6">
                            <q-btn flat class="full-width" @click="changeStatus(props.row, 'closed')" :disable="props.row.status === 'closed'">
                              Close
                            </q-btn>
                          </div>
                          <div class="col-6">
                            <q-btn flat color="grey" class="full-width" @click="archiveTab(props.row)" :disable="props.row.is_archived">
                              Archive
                            </q-btn>
                          </div>
                        </q-card-section>
                      </q-card>
                    </div>

                    <div class="col-12 col-lg-4">
                      <q-card bordered>
                        <q-card-section class="row items-center">
                          <div class="col">
                            <div class="text-subtitle2">Recent Entries</div>
                          </div>
                          <div class="col-auto">
                            <q-btn flat dense icon="refresh" @click="loadTabDetails(props.row.id, true)"></q-btn>
                          </div>
                        </q-card-section>
                        <q-separator></q-separator>
                        <q-list separator>
                          <q-item v-for="entry in tabEntries(props.row.id)" :key="entry.id">
                            <q-item-section>
                              <q-item-label v-text="entry.entry_type"></q-item-label>
                              <q-item-label caption v-text="entry.description || '-'"></q-item-label>
                            </q-item-section>
                            <q-item-section side>
                              <q-item-label v-text="formatEntryAmount(entry, props.row.currency)"></q-item-label>
                              <q-item-label caption v-text="dateFromNow(entry.created_at)"></q-item-label>
                            </q-item-section>
                          </q-item>
                          <q-item v-if="!tabEntries(props.row.id).length">
                            <q-item-section>
                              <q-item-label caption>No entries yet.</q-item-label>
                            </q-item-section>
                          </q-item>
                        </q-list>
                      </q-card>
                    </div>

                    <div class="col-12 col-lg-4">
                      <q-card bordered>
                        <q-card-section class="row items-center">
                          <div class="col">
                            <div class="text-subtitle2">Recent Settlements</div>
                          </div>
                          <div class="col-auto">
                            <q-btn flat dense icon="refresh" @click="loadTabDetails(props.row.id, true)"></q-btn>
                          </div>
                        </q-card-section>
                        <q-separator></q-separator>
                        <q-list separator>
                          <q-item v-for="settlement in tabSettlements(props.row.id)" :key="settlement.id">
                            <q-item-section>
                              <q-item-label v-text="settlement.method"></q-item-label>
                              <q-item-label caption v-text="settlement.reference || '-'"></q-item-label>
                            </q-item-section>
                            <q-item-section side>
                              <q-badge :color="settlementStatusColor(settlement.status)">
                                <span v-text="settlement.status"></span>
                              </q-badge>
                              <q-item-label caption v-text="formatAmount(settlement.amount, props.row.currency)"></q-item-label>
                            </q-item-section>
                          </q-item>
                          <q-item v-if="!tabSettlements(props.row.id).length">
                            <q-item-section>
                              <q-item-label caption>No settlements yet.</q-item-label>
                            </q-item-section>
                          </q-item>
                        </q-list>
                      </q-card>
                    </div>
                  </div>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </div>

    <div class="col-12 col-md-4 col-lg-5 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <h6 class="text-subtitle1 q-my-none">Manual Test Notes</h6>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-list dense>
            <q-item><q-item-section><q-item-label>Create a tab with wallet and currency.</q-item-label></q-item-section></q-item>
            <q-item><q-item-section><q-item-label>Post charges or credits in the tab currency.</q-item-label></q-item-section></q-item>
            <q-item><q-item-section><q-item-label>Use the public page to test Lightning settlement.</q-item-label></q-item-section></q-item>
            <q-item><q-item-section><q-item-label>Watch the balance and status update after payment.</q-item-label></q-item-section></q-item>
          </q-list>
        </q-card-section>
      </q-card>
    </div>

    <q-dialog v-model="tabDialog.show" position="top">
      <q-card v-if="tabDialog.show" class="q-pa-lg q-pt-xl lnbits__dialog-card q-gutter-md">
        <div class="text-h5" v-text="tabDialog.data.id ? 'Edit Tab' : 'New Tab'"></div>

        <q-select
          filled
          dense
          emit-value
          v-model="tabDialog.data.wallet"
          :options="g.user.walletOptions"
          label="Wallet *"
          :disable="Boolean(tabDialog.data.id)"
        ></q-select>
        <q-input filled dense v-model.trim="tabDialog.data.name" label="Name *"></q-input>
        <q-input filled dense v-model.trim="tabDialog.data.customer_name" label="Customer"></q-input>
        <q-input filled dense v-model.trim="tabDialog.data.reference" label="Reference"></q-input>
        <q-select filled dense v-model="tabDialog.data.currency" label="Currency *" :options="currencies"></q-select>
        <q-select
          filled
          dense
          emit-value
          map-options
          v-model="tabDialog.data.limit_type"
          :options="limitTypeOptions"
          label="Limit Type"
        ></q-select>
        <q-input
          v-if="tabDialog.data.limit_type === 'hard'"
          filled
          dense
          v-model.number="tabDialog.data.limit_amount"
          type="number"
          :label="'Limit (' + tabDialog.data.currency + ') *'"
          :step="amountStep(tabDialog.data.currency)"
          :mask="amountMask(tabDialog.data.currency)"
          fill-mask="0"
          reverse-fill-mask
        ></q-input>

        <div class="row justify-end q-gutter-sm">
          <q-btn flat v-close-popup>Cancel</q-btn>
          <q-btn unelevated color="primary" @click="saveTab">Save</q-btn>
        </div>
      </q-card>
    </q-dialog>

    <q-dialog v-model="entryDialog.show" position="top">
      <q-card v-if="entryDialog.show" class="q-pa-lg q-pt-xl lnbits__dialog-card q-gutter-md">
        <div class="text-h5" v-text="entryDialog.title"></div>

        <q-select
          filled
          dense
          emit-value
          map-options
          v-model="entryDialog.data.entry_type"
          :options="entryTypeOptions"
          label="Entry Type"
        ></q-select>
        <q-input
          v-if="entryDialog.data.entry_type !== 'note'"
          filled
          dense
          v-model.number="entryDialog.data.amount"
          type="number"
          :label="'Amount (' + entryDialog.currency + ') *'"
          :step="amountStep(entryDialog.currency)"
          :mask="amountMask(entryDialog.currency)"
          fill-mask="0"
          reverse-fill-mask
        ></q-input>
        <q-input filled dense v-model.trim="entryDialog.data.description" label="Description"></q-input>
        <q-input filled dense v-model.trim="entryDialog.data.source" label="Source"></q-input>
        <q-input filled dense v-model.trim="entryDialog.data.source_id" label="Source ID"></q-input>
        <q-input filled dense v-model.trim="entryDialog.data.idempotency_key" label="Idempotency Key"></q-input>

        <div class="row justify-end q-gutter-sm">
          <q-btn flat v-close-popup>Cancel</q-btn>
          <q-btn unelevated color="primary" @click="saveEntry">Save Entry</q-btn>
        </div>
      </q-card>
    </q-dialog>

    <q-dialog v-model="settlementDialog.show" position="top">
      <q-card v-if="settlementDialog.show" class="q-pa-lg q-pt-xl lnbits__dialog-card q-gutter-md">
        <div class="text-h5">Settle Tab</div>

        <q-banner dense rounded>
          Current balance:
          <span class="text-weight-medium" v-text="formatAmount(settlementDialog.balance, settlementDialog.currency)"></span>
        </q-banner>
        <q-select
          filled
          dense
          emit-value
          map-options
          v-model="settlementDialog.data.method"
          :options="settlementMethodOptions"
          label="Method"
        ></q-select>
        <q-input
          filled
          dense
          v-model.number="settlementDialog.data.amount"
          type="number"
          :label="'Amount (' + settlementDialog.currency + ')'"
          :step="amountStep(settlementDialog.currency)"
          :mask="amountMask(settlementDialog.currency)"
          fill-mask="0"
          reverse-fill-mask
        ></q-input>
        <q-input filled dense v-model.trim="settlementDialog.data.reference" label="Reference"></q-input>
        <q-input filled dense v-model.trim="settlementDialog.data.description" label="Description"></q-input>
        <q-input filled dense v-model.trim="settlementDialog.data.idempotency_key" label="Idempotency Key"></q-input>

        <div class="row justify-end q-gutter-sm">
          <q-btn flat v-close-popup>Cancel</q-btn>
          <q-btn unelevated color="primary" @click="saveSettlement">Create Settlement</q-btn>
        </div>
      </q-card>
    </q-dialog>
  </q-page>
</template>
