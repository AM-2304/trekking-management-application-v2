/* The login and registration screens. */

const LoginView = {
  emits: ['logged-in', 'navigate'],
  data() {
    return { role: 'user', email: '', password: '', error: '', busy: false };
  },
  methods: {
    async submit() {
      this.error = '';
      this.busy = true;
      try {
        const user = await api.post('/api/login', {
          email: this.email, password: this.password, role: this.role,
        });
        this.$emit('logged-in', user);
      } catch (e) {
        this.error = e.message;
      } finally {
        this.busy = false;
      }
    },
    /* Fills the form so nobody has to type passwords during a demo. */
    useDemo(role) {
      this.role = role;
      this.email = { admin: 'admin@tma.local', staff: 'vikram@tma.local', user: 'amit@tma.local' }[role];
      this.password = { admin: 'admin123', staff: 'staff123', user: 'user123' }[role];
    },
  },
  template: `
    <div class="auth-wrap">
      <div class="card shadow-sm auth-card">
        <div class="card-body p-4">
          <h4 class="text-primary fw-bold mb-1">Trekking Management Application</h4>
          <p class="text-muted mb-4">Sign in to your account</p>

          <label class="form-label small fw-semibold">I am signing in as</label>
          <div class="btn-group w-100 mb-3">
            <button v-for="r in [['admin','Admin'],['staff','Trekking Staff'],['user','User (Trekker)']]"
                    :key="r[0]" type="button" class="btn btn-sm"
                    :class="role === r[0] ? 'btn-primary' : 'btn-outline-primary'"
                    @click="role = r[0]">{{ r[1] }}</button>
          </div>

          <form @submit.prevent="submit" novalidate>
            <div class="mb-3">
              <label class="form-label">Email address</label>
              <input v-model.trim="email" type="email" class="form-control" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Password</label>
              <input v-model="password" type="password" class="form-control" required minlength="6">
            </div>
            <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
            <button class="btn btn-primary w-100" :disabled="busy">
              {{ busy ? 'Signing in...' : 'Login' }}
            </button>
          </form>

          <p class="text-center mt-3 mb-0 small">
            Don't have an account?
            <a href="#" @click.prevent="$emit('navigate','register')">Register as User (Trekker)</a>
          </p>

          <div class="alert alert-info small mt-3 mb-0">
            Only Users (Trekkers) can register themselves. Trekking Staff are created by Admin.
            <div class="mt-2">
              Demo logins:
              <a href="#" @click.prevent="useDemo('admin')">admin</a> &middot;
              <a href="#" @click.prevent="useDemo('staff')">staff</a> &middot;
              <a href="#" @click.prevent="useDemo('user')">trekker</a>
            </div>
          </div>
        </div>
      </div>
    </div>`,
};

const RegisterView = {
  emits: ['logged-in', 'navigate'],
  data() {
    return {
      full_name: '', email: '', password: '', confirm: '', contact_number: '',
      error: '', busy: false,
    };
  },
  methods: {
    async submit() {
      this.error = '';
      if (this.password !== this.confirm) {
        this.error = 'The two passwords do not match';
        return;
      }
      this.busy = true;
      try {
        const user = await api.post('/api/register', {
          full_name: this.full_name, email: this.email,
          password: this.password, contact_number: this.contact_number,
        });
        this.$emit('logged-in', user);
      } catch (e) {
        this.error = e.message;
      } finally {
        this.busy = false;
      }
    },
  },
  template: `
    <div class="auth-wrap">
      <div class="card shadow-sm auth-card">
        <div class="card-body p-4">
          <h4 class="fw-bold mb-1">Create User Account</h4>
          <p class="text-muted mb-4">Register as a Trekker</p>

          <form @submit.prevent="submit" novalidate>
            <div class="mb-3">
              <label class="form-label">Full name</label>
              <input v-model.trim="full_name" class="form-control" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Email address</label>
              <input v-model.trim="email" type="email" class="form-control" required>
            </div>
            <div class="mb-3">
              <label class="form-label">Contact number</label>
              <input v-model.trim="contact_number" class="form-control" pattern="[0-9+ -]{7,20}">
            </div>
            <div class="row">
              <div class="col-md-6 mb-3">
                <label class="form-label">Password</label>
                <input v-model="password" type="password" class="form-control" required minlength="6">
              </div>
              <div class="col-md-6 mb-3">
                <label class="form-label">Confirm password</label>
                <input v-model="confirm" type="password" class="form-control" required minlength="6">
              </div>
            </div>
            <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
            <button class="btn btn-primary w-100" :disabled="busy">
              {{ busy ? 'Creating account...' : 'Register' }}
            </button>
          </form>

          <p class="text-center mt-3 mb-0 small">
            Already have an account?
            <a href="#" @click.prevent="$emit('navigate','login')">Login here</a>
          </p>
        </div>
      </div>
    </div>`,
};
