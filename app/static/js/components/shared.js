/*
 * Shared components. Each is a plain object with a `template` string, which is all a
 * Vue component needs - no .vue files and no build step.
 */

/* Coloured status badge. */
const StatusPill = {
  props: ['status'],
  computed: {
    cls() {
      return {
        Open: 'bg-success', Closed: 'bg-secondary', Completed: 'bg-primary',
        Pending: 'bg-warning text-dark', Approved: 'bg-info text-dark',
        Booked: 'bg-success', Cancelled: 'bg-danger',
        Active: 'bg-success', Blacklisted: 'bg-danger',
      }[this.status] || 'bg-secondary';
    },
  },
  template: `<span class="badge" :class="cls">{{ status }}</span>`,
};

/* Hidden when there is only one page. */
const Pagination = {
  props: ['page', 'pages'],
  emits: ['go'],
  template: `
    <nav v-if="pages > 1" class="d-flex justify-content-center mt-3">
      <ul class="pagination mb-0">
        <li class="page-item" :class="{ disabled: page <= 1 }">
          <button class="page-link" @click="$emit('go', page - 1)">&laquo;</button>
        </li>
        <li v-for="n in pages" :key="n" class="page-item" :class="{ active: n === page }">
          <button class="page-link" @click="$emit('go', n)">{{ n }}</button>
        </li>
        <li class="page-item" :class="{ disabled: page >= pages }">
          <button class="page-link" @click="$emit('go', page + 1)">&raquo;</button>
        </li>
      </ul>
    </nav>`,
};

/* Trek card for the browse and dashboard screens. */
const TrekCard = {
  props: ['trek', 'booked'],
  emits: ['book'],
  components: { StatusPill },
  template: `
    <div class="card h-100 shadow-sm">
      <img v-if="trek.image_url" :src="trek.image_url" class="card-img-top trek-img" :alt="trek.name">
      <div v-else class="card-img-top trek-img bg-light d-flex align-items-center justify-content-center text-muted">
        No image
      </div>
      <div class="card-body d-flex flex-column">
        <h5 class="card-title mb-1">{{ trek.name }}</h5>
        <p class="text-muted small mb-2">{{ trek.location }}</p>
        <ul class="list-unstyled small mb-3">
          <li><strong>Difficulty:</strong> {{ trek.difficulty }}</li>
          <li><strong>Duration:</strong> {{ trek.duration_days }} days</li>
          <li><strong>Dates:</strong> {{ trek.start_date }} to {{ trek.end_date }}</li>
          <li :class="trek.available_slots === 0 ? 'text-danger fw-bold' : ''">
            <strong>Slots left:</strong> {{ trek.available_slots }} / {{ trek.total_slots }}
          </li>
        </ul>
        <div class="mt-auto">
          <button v-if="booked" class="btn btn-outline-success w-100" disabled>Already booked</button>
          <button v-else-if="trek.available_slots === 0" class="btn btn-outline-secondary w-100" disabled>
            Not available
          </button>
          <button v-else class="btn btn-primary w-100" @click="$emit('book', trek)">Book now</button>
        </div>
      </div>
    </div>`,
};

/* Corner messages. */
const Toasts = {
  props: ['items'],
  template: `
    <div class="toast-container position-fixed top-0 end-0 p-3" style="z-index:1080">
      <div v-for="t in items" :key="t.id"
           class="toast show align-items-center text-white border-0 mb-2"
           :class="t.type === 'error' ? 'bg-danger' : 'bg-success'">
        <div class="d-flex">
          <div class="toast-body">{{ t.message }}</div>
        </div>
      </div>
    </div>`,
};

/* Sidebar nav; links depend on role. */
const NavSidebar = {
  props: ['user', 'current'],
  emits: ['navigate', 'logout'],
  computed: {
    links() {
      if (this.user.role === 'admin') {
        return [
          ['admin-dashboard', 'Dashboard'], ['admin-treks', 'Treks'],
          ['admin-staff', 'Trekking Staff'], ['admin-users', 'Users (Trekkers)'],
          ['admin-bookings', 'Bookings'], ['admin-reports', 'Reports'],
        ];
      }
      if (this.user.role === 'staff') {
        return [['staff-dashboard', 'Dashboard'], ['staff-profile', 'Profile']];
      }
      return [
        ['user-dashboard', 'Dashboard'], ['user-browse', 'Browse Treks'],
        ['user-bookings', 'My Bookings'], ['user-history', 'History'],
        ['user-profile', 'Profile'],
      ];
    },
  },
  template: `
    <div class="sidebar bg-white border-end p-3">
      <h6 class="text-primary fw-bold mb-3">Trekking Management</h6>
      <ul class="nav flex-column">
        <li v-for="[key, label] in links" :key="key" class="nav-item">
          <a href="#" class="nav-link py-2" :class="current === key ? 'active fw-semibold' : 'text-dark'"
             @click.prevent="$emit('navigate', key)">{{ label }}</a>
        </li>
        <li class="nav-item mt-2 border-top pt-2">
          <a href="#" class="nav-link py-2 text-danger" @click.prevent="$emit('logout')">Logout</a>
        </li>
      </ul>
    </div>`,
};
