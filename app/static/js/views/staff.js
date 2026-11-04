/* Trek staff screens. */

const StaffDashboard = {
  components: { StatusPill },
  emits: ['manage'],
  data() { return { data: null }; },
  async mounted() { this.data = await api.get('/api/staff/treks'); },
  template: `
    <div v-if="data">
      <h4 class="mb-4">My Dashboard</h4>
      <div class="row g-3 mb-4">
        <div class="col-6 col-lg-4" v-for="c in [
          ['Assigned Treks', data.assigned_count],
          ['Total Participants', data.total_participants],
          ['Ongoing Treks', data.ongoing_count]]" :key="c[0]">
          <div class="card shadow-sm h-100"><div class="card-body">
            <div class="text-muted small">{{ c[0] }}</div>
            <div class="display-6 fw-bold">{{ c[1] }}</div>
          </div></div>
        </div>
      </div>

      <div class="card shadow-sm"><div class="card-body">
        <h6 class="mb-3">My Assigned Treks</h6>
        <div class="table-responsive">
          <table class="table align-middle mb-0">
            <thead><tr>
              <th>Trek Name</th><th>Dates</th><th>Participants</th>
              <th>Slots</th><th>Status</th><th>Action</th>
            </tr></thead>
            <tbody>
              <tr v-for="t in data.items" :key="t.id">
                <td>{{ t.name }}</td>
                <td class="small">{{ t.start_date }} to {{ t.end_date }}</td>
                <td>{{ t.participants }}</td>
                <td>{{ t.available_slots }} / {{ t.total_slots }}</td>
                <td><status-pill :status="t.status"></status-pill></td>
                <td><button class="btn btn-sm btn-primary" @click="$emit('manage', t.id)">Manage</button></td>
              </tr>
              <tr v-if="!data.items.length">
                <td colspan="6" class="text-muted text-center py-3">
                  No treks are assigned to you yet.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div></div>
    </div>`,
};

const StaffManageTrek = {
  components: { StatusPill },
  props: ['trekId'],
  inject: ['toast'],
  emits: ['back'],
  data() { return { trek: null, participants: [], slots: 0, status: '' }; },
  async mounted() { await this.load(); },
  methods: {
    async load() {
      const d = await api.get(`/api/staff/treks/${this.trekId}/participants`);
      this.trek = d.trek;
      this.participants = d.items;
      this.slots = d.trek.available_slots;
      this.status = d.trek.status === 'Open' || d.trek.status === 'Closed'
        ? d.trek.status : 'Open';
    },
    async save() {
      try {
        await api.put(`/api/staff/treks/${this.trekId}`, {
          available_slots: Number(this.slots), status: this.status,
        });
        this.toast('Trek updated');
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
    async complete() {
      if (!confirm('Mark this trek as completed? Every active booking will be marked completed too.')) return;
      try {
        await api.put(`/api/staff/treks/${this.trekId}`, { status: 'Completed' });
        this.toast('Trek marked as completed');
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
  },
  template: `
    <div v-if="trek">
      <button class="btn btn-sm btn-link ps-0 mb-2" @click="$emit('back')">&larr; Back to My Treks</button>
      <h4 class="mb-3">{{ trek.name }}</h4>

      <div class="row g-3">
        <div class="col-lg-5">
          <div class="card shadow-sm h-100"><div class="card-body">
            <h6 class="mb-3">Trek Details</h6>
            <dl class="row small mb-3">
              <dt class="col-6">Location</dt><dd class="col-6">{{ trek.location }}</dd>
              <dt class="col-6">Difficulty</dt><dd class="col-6">{{ trek.difficulty }}</dd>
              <dt class="col-6">Duration</dt><dd class="col-6">{{ trek.duration_days }} days</dd>
              <dt class="col-6">Start Date</dt><dd class="col-6">{{ trek.start_date }}</dd>
              <dt class="col-6">End Date</dt><dd class="col-6">{{ trek.end_date }}</dd>
              <dt class="col-6">Total Slots</dt><dd class="col-6">{{ trek.total_slots }}</dd>
              <dt class="col-6">Current Status</dt>
              <dd class="col-6"><status-pill :status="trek.status"></status-pill></dd>
            </dl>

            <div v-if="trek.status !== 'Completed'">
              <form @submit.prevent="save">
                <div class="mb-2">
                  <label class="form-label small fw-semibold">Available Slots</label>
                  <input v-model="slots" type="number" min="0" :max="trek.total_slots"
                         class="form-control form-control-sm" required>
                </div>
                <div class="mb-3">
                  <label class="form-label small fw-semibold">Status</label>
                  <select v-model="status" class="form-select form-select-sm">
                    <option>Open</option><option>Closed</option>
                  </select>
                </div>
                <button class="btn btn-primary btn-sm w-100 mb-2">Update Trek</button>
              </form>
              <button class="btn btn-outline-success btn-sm w-100" @click="complete">
                Mark as Completed
              </button>
            </div>
            <div v-else class="alert alert-success small mb-0">
              This trek is complete. It can no longer be edited.
            </div>
          </div></div>
        </div>

        <div class="col-lg-7">
          <div class="card shadow-sm h-100"><div class="card-body">
            <h6 class="mb-3">Participants ({{ participants.length }})</h6>
            <div class="table-responsive">
              <table class="table table-sm align-middle mb-0">
                <thead><tr><th>#</th><th>Name</th><th>Email</th><th>Booking Date</th><th>Status</th></tr></thead>
                <tbody>
                  <tr v-for="(p, i) in participants" :key="p.id">
                    <td>{{ i + 1 }}</td><td>{{ p.user_name }}</td><td class="small">{{ p.user_email }}</td>
                    <td class="small">{{ p.booking_date.slice(0,10) }}</td>
                    <td><status-pill :status="p.status"></status-pill></td>
                  </tr>
                  <tr v-if="!participants.length">
                    <td colspan="5" class="text-muted text-center py-3">Nobody has booked this trek yet.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div></div>
        </div>
      </div>
    </div>`,
};
