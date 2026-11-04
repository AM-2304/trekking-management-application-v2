/* Admin screens. */

const AdminDashboard = {
  components: { StatusPill },
  data() {
    return { stats: null };
  },
  async mounted() {
    this.stats = await api.get('/api/admin/stats');
  },
  template: `
    <div v-if="stats">
      <h4 class="mb-4">Dashboard</h4>
      <div class="row g-3 mb-4">
        <div class="col-6 col-lg-3" v-for="c in [
          ['Total Treks', stats.total_treks],
          ['Total Users (Trekkers)', stats.total_users],
          ['Total Trekking Staff', stats.total_staff],
          ['Total Bookings', stats.total_bookings]]" :key="c[0]">
          <div class="card shadow-sm h-100">
            <div class="card-body">
              <div class="text-muted small">{{ c[0] }}</div>
              <div class="display-6 fw-bold">{{ c[1] }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card shadow-sm">
        <div class="card-body">
          <h6 class="mb-3">Recent Bookings</h6>
          <div class="table-responsive">
            <table class="table table-sm align-middle mb-0">
              <thead><tr>
                <th>Booking ID</th><th>User (Trekker)</th><th>Trek</th>
                <th>Booking Date</th><th>Status</th>
              </tr></thead>
              <tbody>
                <tr v-for="b in stats.recent_bookings" :key="b.id">
                  <td>{{ b.code }}</td><td>{{ b.user_name }}</td><td>{{ b.trek_name }}</td>
                  <td>{{ b.booking_date.slice(0,10) }}</td>
                  <td><status-pill :status="b.status"></status-pill></td>
                </tr>
                <tr v-if="!stats.recent_bookings.length">
                  <td colspan="5" class="text-muted text-center py-3">No bookings yet.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>`,
};

const AdminTreks = {
  components: { StatusPill, Pagination },
  inject: ['toast'],
  data() {
    return { data: null, q: '', page: 1, editing: null, staff: [] };
  },
  async mounted() {
    this.staff = (await api.get('/api/admin/staff')).items;
    this.load();
  },
  methods: {
    async load() {
      this.data = await api.get(`/api/admin/treks?q=${encodeURIComponent(this.q)}&page=${this.page}`);
    },
    search() { this.page = 1; this.load(); },
    go(n) { this.page = n; this.load(); },
    blank() {
      return {
        name: '', location: '', difficulty: 'Easy', total_slots: 10,
        status: 'Pending', start_date: '', end_date: '', image_url: '',
        instructions: '', assigned_staff_id: null,
      };
    },
    create() { this.editing = this.blank(); },
    edit(trek) { this.editing = { ...trek }; },
    async save() {
      try {
        const body = { ...this.editing, total_slots: Number(this.editing.total_slots) };
        if (body.assigned_staff_id) body.assigned_staff_id = Number(body.assigned_staff_id);
        if (body.id) await api.put(`/api/admin/treks/${body.id}`, body);
        else await api.post('/api/admin/treks', body);
        this.editing = null;
        this.toast('Trek saved');
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
    async remove(trek) {
      if (!confirm(`Delete "${trek.name}"? This cannot be undone.`)) return;
      try {
        await api.del(`/api/admin/treks/${trek.id}`);
        this.toast('Trek deleted');
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="mb-0">Treks</h4>
        <button class="btn btn-primary" @click="create()">+ Add New Trek</button>
      </div>

      <div class="card shadow-sm">
        <div class="card-body">
          <input v-model.trim="q" @input="search" class="form-control mb-3"
                 placeholder="Search treks by name or location...">
          <div class="table-responsive">
            <table class="table align-middle">
              <thead><tr>
                <th>ID</th><th>Trek Name</th><th>Location</th><th>Difficulty</th>
                <th>Slots</th><th>Staff</th><th>Status</th><th>Actions</th>
              </tr></thead>
              <tbody>
                <tr v-for="t in (data ? data.items : [])" :key="t.id">
                  <td>{{ t.id }}</td><td>{{ t.name }}</td><td>{{ t.location }}</td>
                  <td>{{ t.difficulty }}</td>
                  <td>{{ t.available_slots }} / {{ t.total_slots }}</td>
                  <td class="small">{{ t.assigned_staff_name || '-' }}</td>
                  <td><status-pill :status="t.status"></status-pill></td>
                  <td class="text-nowrap">
                    <button class="btn btn-sm btn-outline-primary me-1" @click="edit(t)">Edit</button>
                    <button class="btn btn-sm btn-outline-danger" @click="remove(t)">Delete</button>
                  </td>
                </tr>
                <tr v-if="data && !data.items.length">
                  <td colspan="8" class="text-muted text-center py-3">No treks found.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <pagination v-if="data" :page="data.page" :pages="data.pages" @go="go"></pagination>
        </div>
      </div>

      <!-- Inline form instead of a modal, to keep things simple. -->
      <div v-if="editing" class="card shadow-sm mt-3 border-primary">
        <div class="card-body">
          <h6 class="mb-3">{{ editing.id ? 'Edit Trek' : 'Add New Trek' }}</h6>
          <form @submit.prevent="save">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Trek name</label>
                <input v-model.trim="editing.name" class="form-control" required>
              </div>
              <div class="col-md-6">
                <label class="form-label">Location</label>
                <input v-model.trim="editing.location" class="form-control" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">Difficulty</label>
                <select v-model="editing.difficulty" class="form-select">
                  <option>Easy</option><option>Moderate</option><option>Hard</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Total slots</label>
                <input v-model="editing.total_slots" type="number" min="1" class="form-control" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">Status</label>
                <select v-model="editing.status" class="form-select">
                  <option>Pending</option><option>Approved</option><option>Open</option>
                  <option>Closed</option><option>Completed</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label">Start date</label>
                <input v-model="editing.start_date" type="date" class="form-control" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">End date</label>
                <input v-model="editing.end_date" type="date" class="form-control" required>
              </div>
              <div class="col-md-4">
                <label class="form-label">Assigned staff</label>
                <select v-model="editing.assigned_staff_id" class="form-select">
                  <option :value="null">- none -</option>
                  <option v-for="s in staff" :key="s.id" :value="s.id">{{ s.full_name }}</option>
                </select>
              </div>
              <div class="col-12">
                <label class="form-label">Image URL</label>
                <input v-model.trim="editing.image_url" class="form-control" type="url">
              </div>
              <div class="col-12">
                <label class="form-label">Instructions (sent in reminder emails)</label>
                <textarea v-model.trim="editing.instructions" class="form-control" rows="2"></textarea>
              </div>
            </div>
            <div class="mt-3">
              <button class="btn btn-primary me-2">Save Trek</button>
              <button type="button" class="btn btn-outline-secondary" @click="editing = null">Cancel</button>
            </div>
          </form>
        </div>
      </div>
    </div>`,
};

const AdminStaff = {
  components: { StatusPill },
  inject: ['toast'],
  data() {
    return { items: [], q: '', creating: null };
  },
  mounted() { this.load(); },
  methods: {
    async load() {
      this.items = (await api.get(`/api/admin/staff?q=${encodeURIComponent(this.q)}`)).items;
    },
    create() {
      this.creating = {
        full_name: '', email: '', contact_number: '', password: '',
        confirm: '', experience: '', specialization: '',
      };
    },
    async save() {
      if (this.creating.password !== this.creating.confirm) {
        this.toast('The two passwords do not match', 'error');
        return;
      }
      try {
        await api.post('/api/admin/staff', this.creating);
        this.creating = null;
        this.toast('Staff member created - credentials written to the outbox');
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
    async toggle(member) {
      try {
        await api.put(`/api/admin/users/${member.id}/blacklist`, {});
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
  },
  template: `
    <div>
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h4 class="mb-0">Trekking Staff</h4>
        <button class="btn btn-primary" @click="create()">+ Create New Staff</button>
      </div>

      <div class="card shadow-sm">
        <div class="card-body">
          <input v-model.trim="q" @input="load" class="form-control mb-3" placeholder="Search staff...">
          <div class="table-responsive">
            <table class="table align-middle">
              <thead><tr>
                <th>ID</th><th>Name</th><th>Email</th><th>Contact</th>
                <th>Experience</th><th>Specialization</th><th>Status</th><th>Action</th>
              </tr></thead>
              <tbody>
                <tr v-for="s in items" :key="s.id">
                  <td>{{ s.code }}</td><td>{{ s.full_name }}</td><td>{{ s.email }}</td>
                  <td>{{ s.contact_number || '-' }}</td><td>{{ s.experience || '-' }}</td>
                  <td>{{ s.specialization || '-' }}</td>
                  <td><status-pill :status="s.is_blacklisted ? 'Blacklisted' : 'Active'"></status-pill></td>
                  <td>
                    <button class="btn btn-sm"
                            :class="s.is_blacklisted ? 'btn-outline-success' : 'btn-outline-danger'"
                            @click="toggle(s)">
                      {{ s.is_blacklisted ? 'Whitelist' : 'Blacklist' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="!items.length">
                  <td colspan="8" class="text-muted text-center py-3">No staff found.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="alert alert-info small mb-0">Blacklisted staff cannot login or access the system.</div>
        </div>
      </div>

      <div v-if="creating" class="card shadow-sm mt-3 border-primary">
        <div class="card-body">
          <h6 class="mb-3">Create New Trekking Staff</h6>
          <form @submit.prevent="save">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Full name</label>
                <input v-model.trim="creating.full_name" class="form-control" required>
              </div>
              <div class="col-md-6">
                <label class="form-label">Email address</label>
                <input v-model.trim="creating.email" type="email" class="form-control" required>
              </div>
              <div class="col-md-6">
                <label class="form-label">Contact number</label>
                <input v-model.trim="creating.contact_number" class="form-control">
              </div>
              <div class="col-md-6">
                <label class="form-label">Experience</label>
                <input v-model.trim="creating.experience" class="form-control" placeholder="e.g. 5 years">
              </div>
              <div class="col-md-6">
                <label class="form-label">Password</label>
                <input v-model="creating.password" type="password" class="form-control" required minlength="6">
              </div>
              <div class="col-md-6">
                <label class="form-label">Confirm password</label>
                <input v-model="creating.confirm" type="password" class="form-control" required minlength="6">
              </div>
              <div class="col-12">
                <label class="form-label">Specialization</label>
                <input v-model.trim="creating.specialization" class="form-control"
                       placeholder="e.g. High Altitude, First Aid">
              </div>
            </div>
            <div class="mt-3">
              <button class="btn btn-primary me-2">Create Staff</button>
              <button type="button" class="btn btn-outline-secondary" @click="creating = null">Cancel</button>
            </div>
          </form>
        </div>
      </div>
    </div>`,
};

const AdminUsers = {
  components: { StatusPill },
  inject: ['toast'],
  data() { return { items: [], q: '' }; },
  mounted() { this.load(); },
  methods: {
    async load() {
      this.items = (await api.get(`/api/admin/users?q=${encodeURIComponent(this.q)}`)).items;
    },
    async toggle(user) {
      try {
        await api.put(`/api/admin/users/${user.id}/blacklist`, {});
        this.load();
      } catch (e) { this.toast(e.message, 'error'); }
    },
  },
  template: `
    <div>
      <h4 class="mb-3">Users (Trekkers)</h4>
      <div class="card shadow-sm">
        <div class="card-body">
          <input v-model.trim="q" @input="load" class="form-control mb-3" placeholder="Search users...">
          <div class="table-responsive">
            <table class="table align-middle">
              <thead><tr>
                <th>ID</th><th>Name</th><th>Email</th><th>Contact</th><th>Status</th><th>Action</th>
              </tr></thead>
              <tbody>
                <tr v-for="u in items" :key="u.id">
                  <td>{{ u.code }}</td><td>{{ u.full_name }}</td><td>{{ u.email }}</td>
                  <td>{{ u.contact_number || '-' }}</td>
                  <td><status-pill :status="u.is_blacklisted ? 'Blacklisted' : 'Active'"></status-pill></td>
                  <td>
                    <button class="btn btn-sm"
                            :class="u.is_blacklisted ? 'btn-outline-success' : 'btn-outline-danger'"
                            @click="toggle(u)">
                      {{ u.is_blacklisted ? 'Whitelist' : 'Blacklist' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="!items.length">
                  <td colspan="6" class="text-muted text-center py-3">No users found.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="alert alert-info small mb-0">Blacklisted users cannot login or book treks.</div>
        </div>
      </div>
    </div>`,
};

const AdminBookings = {
  components: { StatusPill, Pagination },
  data() { return { data: null, page: 1 }; },
  mounted() { this.load(); },
  methods: {
    async load() { this.data = await api.get(`/api/admin/bookings?page=${this.page}`); },
    go(n) { this.page = n; this.load(); },
  },
  template: `
    <div>
      <h4 class="mb-3">All Bookings</h4>
      <div class="card shadow-sm"><div class="card-body">
        <div class="table-responsive">
          <table class="table align-middle">
            <thead><tr>
              <th>Booking ID</th><th>User</th><th>Trek</th><th>Location</th>
              <th>Booking Date</th><th>Trek Dates</th><th>Status</th>
            </tr></thead>
            <tbody>
              <tr v-for="b in (data ? data.items : [])" :key="b.id">
                <td>{{ b.code }}</td><td>{{ b.user_name }}</td><td>{{ b.trek_name }}</td>
                <td>{{ b.location }}</td><td>{{ b.booking_date.slice(0,10) }}</td>
                <td class="small">{{ b.start_date }} to {{ b.end_date }}</td>
                <td><status-pill :status="b.status"></status-pill></td>
              </tr>
              <tr v-if="data && !data.items.length">
                <td colspan="7" class="text-muted text-center py-3">No bookings yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <pagination v-if="data" :page="data.page" :pages="data.pages" @go="go"></pagination>
      </div></div>
    </div>`,
};

/* Runs the scheduled jobs on demand instead of waiting for Celery beat. */
const AdminReports = {
  inject: ['toast'],
  data() { return { busy: '' }; },
  methods: {
    async run(job, label) {
      this.busy = job;
      try {
        const r = await api.post(`/api/admin/jobs/${job}`, {});
        this.toast(`${label}: ${r.result}`);
      } catch (e) {
        this.toast(e.message, 'error');
      } finally { this.busy = ''; }
    },
  },
  template: `
    <div>
      <h4 class="mb-3">Reports &amp; Background Jobs</h4>
      <div class="card shadow-sm"><div class="card-body">
        <p class="text-muted small">
          These jobs normally run on a schedule through Celery: reminders every day at 08:00
          and the activity report on the 1st of each month. The buttons below run them
          immediately. Output is written to <code>instance/outbox/</code> as HTML files.
        </p>
        <button class="btn btn-outline-primary me-2" :disabled="busy"
                @click="run('daily-reminders','Daily reminders')">
          {{ busy === 'daily-reminders' ? 'Running...' : 'Run daily reminders now' }}
        </button>
        <button class="btn btn-outline-primary" :disabled="busy"
                @click="run('monthly-report','Monthly report')">
          {{ busy === 'monthly-report' ? 'Running...' : 'Generate monthly report now' }}
        </button>
      </div></div>
    </div>`,
};
