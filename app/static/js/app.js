/*
 * Root Vue app. Routing is hand-written instead of vue-router: `view` is a string
 * kept in sync with location.hash, and <component :is> renders whatever it names.
 */

const { createApp, reactive } = Vue;

/* Route name -> component. */
const ROUTES = {
  login: 'LoginView',
  register: 'RegisterView',

  'admin-dashboard': 'AdminDashboard',
  'admin-treks': 'AdminTreks',
  'admin-staff': 'AdminStaff',
  'admin-users': 'AdminUsers',
  'admin-bookings': 'AdminBookings',
  'admin-reports': 'AdminReports',

  'staff-dashboard': 'StaffDashboard',
  'staff-manage': 'StaffManageTrek',
  'staff-profile': 'StaffProfile',

  'user-dashboard': 'UserDashboard',
  'user-browse': 'UserBrowse',
  'user-bookings': 'UserBookings',
  'user-history': 'UserHistory',
  'user-profile': 'UserProfile',
};

/* Landing screen per role. */
const HOME = { admin: 'admin-dashboard', staff: 'staff-dashboard', user: 'user-dashboard' };

const App = {
  components: {
    NavSidebar, Toasts,
    LoginView, RegisterView,
    AdminDashboard, AdminTreks, AdminStaff, AdminUsers, AdminBookings, AdminReports,
    StaffDashboard, StaffManageTrek, StaffProfile,
    UserDashboard, UserBrowse, UserBookings, UserHistory, UserProfile,
  },

  data() {
    return {
      user: null,
      ready: false,     // false while the session check is in flight
      view: 'login',
      manageTrekId: null,
      toasts: [],
      nextToastId: 1,
    };
  },

  /* Lets any child call this.toast(...) without prop drilling. */
  provide() {
    return { toast: (message, type) => this.pushToast(message, type) };
  },

  computed: {
    component() { return ROUTES[this.view] || 'LoginView'; },
  },

  async mounted() {
    // Restore an existing session if the cookie is still valid.
    try {
      this.user = await api.get('/api/me');
      this.view = this.routeFromHash() || HOME[this.user.role];
    } catch {
      this.user = null;
      this.view = this.routeFromHash() === 'register' ? 'register' : 'login';
    } finally {
      this.ready = true;
    }

    // Keeps the back/forward buttons working.
    window.addEventListener('hashchange', () => {
      const route = this.routeFromHash();
      if (route && route !== this.view) this.view = route;
    });
  },

  methods: {
    routeFromHash() {
      const name = window.location.hash.replace(/^#\/?/, '');
      return ROUTES[name] ? name : null;
    },

    navigate(view) {
      this.view = view;
      window.location.hash = '#/' + view;
    },

    onLoggedIn(user) {
      this.user = user;
      this.navigate(HOME[user.role]);
    },

    async logout() {
      await api.post('/api/logout', {});
      this.user = null;
      this.navigate('login');
    },

    manageTrek(trekId) {
      this.manageTrekId = trekId;
      this.navigate('staff-manage');
    },

    pushToast(message, type = 'success') {
      const id = this.nextToastId++;
      this.toasts.push({ id, message, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter((t) => t.id !== id);
      }, 4000);
    },
  },

  template: `
    <div v-if="!ready" class="text-center text-muted py-5">Loading...</div>

    <!-- Signed out -->
    <div v-else-if="!user">
      <component :is="component" @logged-in="onLoggedIn" @navigate="navigate"></component>
      <toasts :items="toasts"></toasts>
    </div>

    <!-- Signed in -->
    <div v-else class="app-shell">
      <nav-sidebar :user="user" :current="view" @navigate="navigate" @logout="logout"></nav-sidebar>

      <div class="flex-grow-1 min-width-0">
        <header class="bg-white border-bottom px-3 px-md-4 py-2 d-flex justify-content-between align-items-center">
          <span class="fw-semibold text-primary">Trekking Management Application</span>
          <span class="small text-muted">
            {{ user.full_name }}
            <span class="badge bg-light text-dark border ms-1 text-capitalize">{{ user.role }}</span>
          </span>
        </header>

        <main class="p-3 p-md-4">
          <component
            :is="component"
            :user="user"
            :trek-id="manageTrekId"
            @manage="manageTrek"
            @back="navigate('staff-dashboard')"
            @updated="user = $event">
          </component>
        </main>
      </div>

      <toasts :items="toasts"></toasts>
    </div>`,
};

createApp(App).mount('#app');
