/* Trekker screens. */

/* Search box, filters and trek cards; used by the dashboard and browse screens. */
const TrekBrowser = {
  components: { TrekCard, Pagination },
  props: ['bookedIds', 'compact'],
  inject: ['toast'],
  emits: ['booked'],
  data() {
    return { data: null, q: '', difficulty: '', location: '', duration: '', page: 1 };
  },
  mounted() { this.load(); },
  methods: {
    async load() {
      const params = new URLSearchParams({
        q: this.q, difficulty: this.difficulty, location: this.location, page: this.page,
      });
      if (this.duration) params.set('duration', this.duration);
      this.data = await api.get('/api/treks?' + params.toString());
    },
    search() { this.page = 1; this.load(); },
    go(n) { this.page = n; this.load(); },
    async book(trek) {
      try {
        await api.post('/api/bookings', { trek_id: trek.id });
        this.toast(`Booked ${trek.name}`);
        this.$emit('booked');
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
  },
  template: `
    <div>
      <div class="row g-2 mb-3">
        <div class="col-12 col-md">
          <input v-model.trim="q" @input="search" class="form-control" placeholder="Search treks...">
        </div>
        <div class="col-6 col-md-auto">
          <select v-model="difficulty" @change="search" class="form-select">
            <option value="">Difficulty: All</option>
            <option>Easy</option><option>Moderate</option><option>Hard</option>
          </select>
        </div>
        <div class="col-6 col-md-auto">
          <select v-model="location" @change="search" class="form-select">
            <option value="">Location: All</option>
            <option v-for="l in (data ? data.locations : [])" :key="l">{{ l }}</option>
          </select>
        </div>
        <div class="col-6 col-md-auto">
          <select v-model="duration" @change="search" class="form-select">
            <option value="">Duration: Any</option>
            <option value="5">Up to 5 days</option>
            <option value="10">Up to 10 days</option>
            <option value="20">Up to 20 days</option>
          </select>
        </div>
      </div>

      <div class="row g-3">
        <div v-for="t in (data ? data.items : [])" :key="t.id" class="col-12 col-sm-6 col-xl-4">
          <trek-card :trek="t" :booked="bookedIds.includes(t.id)" @book="book"></trek-card>
        </div>
        <div v-if="data && !data.items.length" class="col-12">
          <div class="alert alert-light text-center text-muted mb-0">
            No treks match your search.
          </div>
        </div>
      </div>

      <pagination v-if="data && !compact" :page="data.page" :pages="data.pages" @go="go"></pagination>
    </div>`,
};

const UserDashboard = {
  components: { TrekBrowser, StatusPill },
  props: ['user'],
  data() { return { bookings: { active: [], history: [] } }; },
  computed: {
    bookedIds() { return this.bookings.active.map((b) => b.trek_id); },
  },
  mounted() { this.loadBookings(); },
  methods: {
    async loadBookings() { this.bookings = await api.get('/api/my/bookings'); },
  },
  template: `
    <div>
      <h4 class="mb-4">Welcome, {{ user.full_name.split(' ')[0] }}!</h4>

      <h6 class="mb-3">Available Treks</h6>
      <trek-browser :booked-ids="bookedIds" :compact="true" @booked="loadBookings"></trek-browser>

      <h6 class="mt-4 mb-3">My Bookings</h6>
      <div class="card shadow-sm"><div class="card-body">
        <div class="table-responsive">
          <table class="table table-sm align-middle mb-0">
            <thead><tr><th>Trek Name</th><th>Booking Date</th><th>Trek Dates</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="b in bookings.active" :key="b.id">
                <td>{{ b.trek_name }}</td><td>{{ b.booking_date.slice(0,10) }}</td>
                <td class="small">{{ b.start_date }} to {{ b.end_date }}</td>
                <td><status-pill :status="b.status"></status-pill></td>
              </tr>
              <tr v-if="!bookings.active.length">
                <td colspan="4" class="text-muted text-center py-3">You have no active bookings.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div></div>
    </div>`,
};

const UserBrowse = {
  components: { TrekBrowser },
  data() { return { bookedIds: [] }; },
  mounted() { this.load(); },
  methods: {
    async load() {
      this.bookedIds = (await api.get('/api/my/bookings')).active.map((b) => b.trek_id);
    },
  },
  template: `
    <div>
      <h4 class="mb-3">Browse Treks</h4>
      <trek-browser :booked-ids="bookedIds" @booked="load"></trek-browser>
    </div>`,
};

const UserBookings = {
  components: { StatusPill },
  inject: ['toast'],
  data() { return { bookings: { active: [], history: [] } }; },
  mounted() { this.load(); },
  methods: {
    async load() { this.bookings = await api.get('/api/my/bookings'); },
    async cancel(b) {
      if (!confirm(`Cancel your booking for "${b.trek_name}"?`)) return;
      try {
        await api.put(`/api/bookings/${b.id}/cancel`);
        this.toast('Booking cancelled');
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
  },
  template: `
    <div>
      <h4 class="mb-3">My Bookings</h4>
      <div class="card shadow-sm"><div class="card-body">
        <div class="table-responsive">
          <table class="table align-middle mb-0">
            <thead><tr>
              <th>Trek Name</th><th>Location</th><th>Booking Date</th>
              <th>Trek Dates</th><th>Status</th><th>Action</th>
            </tr></thead>
            <tbody>
              <tr v-for="b in bookings.active" :key="b.id">
                <td>{{ b.trek_name }}</td><td>{{ b.location }}</td>
                <td>{{ b.booking_date.slice(0,10) }}</td>
                <td class="small">{{ b.start_date }} to {{ b.end_date }}</td>
                <td><status-pill :status="b.status"></status-pill></td>
                <td><button class="btn btn-sm btn-outline-danger" @click="cancel(b)">Cancel</button></td>
              </tr>
              <tr v-if="!bookings.active.length">
                <td colspan="6" class="text-muted text-center py-3">You have no active bookings.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div></div>
    </div>`,
};

const UserHistory = {
  components: { StatusPill },
  data() { return { history: [] }; },
  async mounted() {
    this.history = (await api.get('/api/my/bookings')).history;
  },
  template: `
    <div>
      <h4 class="mb-3">Trekking History</h4>
      <div class="card shadow-sm"><div class="card-body">
        <div class="table-responsive">
          <table class="table align-middle mb-0">
            <thead><tr>
              <th>Trek Name</th><th>Location</th><th>Trek Dates</th><th>Booked On</th><th>Status</th>
            </tr></thead>
            <tbody>
              <tr v-for="b in history" :key="b.id">
                <td>{{ b.trek_name }}</td><td>{{ b.location }}</td>
                <td class="small">{{ b.start_date }} to {{ b.end_date }}</td>
                <td>{{ b.booking_date.slice(0,10) }}</td>
                <td><status-pill :status="b.status"></status-pill></td>
              </tr>
              <tr v-if="!history.length">
                <td colspan="5" class="text-muted text-center py-3">Nothing here yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="alert alert-info small mt-3 mb-0">
          History shows all your completed and cancelled treks.
        </div>
      </div></div>
    </div>`,
};

const UserProfile = {
  props: ['user'],
  inject: ['toast'],
  emits: ['updated'],
  data() {
    return {
      form: {
        full_name: this.user.full_name,
        contact_number: this.user.contact_number || '',
        password: '',
      },
      exporting: false,
      download: null,
    };
  },
  methods: {
    async save() {
      try {
        const body = { full_name: this.form.full_name, contact_number: this.form.contact_number };
        if (this.form.password) body.password = this.form.password;
        const updated = await api.put('/api/me', body);
        this.form.password = '';
        this.toast('Profile updated');
        this.$emit('updated', updated);
      } catch (e) { this.toast(e.message, 'error'); }
    },

    /* Start the export, then poll once a second until the worker reports it done. */
    async exportCsv() {
      this.exporting = true;
      this.download = null;
      try {
        const { task_id } = await api.post('/api/export', {});
        this.toast('Export started - preparing your file...');

        for (let attempt = 0; attempt < 30; attempt++) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          const status = await api.get(`/api/export/${task_id}`);

          if (status.status === 'done') {
            this.download = `/api/export/download/${status.filename}`;
            this.toast('Your export is ready to download');
            return;
          }
          if (status.status === 'failed') {
            this.toast('The export failed', 'error');
            return;
          }
        }
        this.toast('The export is taking too long. Is the Celery worker running?', 'error');
      } catch (e) {
        this.toast(e.message, 'error');
      } finally {
        this.exporting = false;
      }
    },
  },
  template: `
    <div>
      <h4 class="mb-3">My Profile</h4>
      <div class="row g-3">
        <div class="col-lg-6">
          <div class="card shadow-sm h-100"><div class="card-body">
            <h6 class="mb-3">Edit Details</h6>
            <form @submit.prevent="save">
              <div class="mb-3">
                <label class="form-label">Email (cannot be changed)</label>
                <input :value="user.email" class="form-control" disabled>
              </div>
              <div class="mb-3">
                <label class="form-label">Full name</label>
                <input v-model.trim="form.full_name" class="form-control" required>
              </div>
              <div class="mb-3">
                <label class="form-label">Contact number</label>
                <input v-model.trim="form.contact_number" class="form-control">
              </div>
              <div class="mb-3">
                <label class="form-label">New password <span class="text-muted small">(leave blank to keep)</span></label>
                <input v-model="form.password" type="password" class="form-control" minlength="6">
              </div>
              <button class="btn btn-primary">Save Changes</button>
            </form>
          </div></div>
        </div>

        <div class="col-lg-6">
          <div class="card shadow-sm h-100"><div class="card-body">
            <h6 class="mb-3">Export Trekking History</h6>
            <p class="text-muted small">
              Download every booking you have made as a CSV file. The file is produced by a
              background job, so this takes a moment.
            </p>
            <button class="btn btn-outline-primary" :disabled="exporting" @click="exportCsv">
              {{ exporting ? 'Preparing...' : 'Export as CSV' }}
            </button>
            <div v-if="download" class="alert alert-success small mt-3 mb-0">
              <a :href="download">Download your CSV</a>
            </div>
          </div></div>
        </div>
      </div>
    </div>`,
};

/* Staff reuse the profile screen. */
const StaffProfile = {
  props: ['user'],
  components: { UserProfile },
  template: `<user-profile :user="user"></user-profile>`,
};
