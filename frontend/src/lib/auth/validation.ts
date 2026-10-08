const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export interface RegistrationValues {
  email: string;
  password: string;
  confirmPassword: string;
  firstName: string;
  lastName: string;
  tenantName: string;
}

export function validateLogin(email: string, password: string): string | null {
  if (!email.trim() || !password) return "Enter your email and password.";
  if (!EMAIL_PATTERN.test(email.trim())) return "Enter a valid email address.";
  if (password.length > 128) return "Password must be 128 characters or fewer.";
  return null;
}

export function validateRegistration(values: RegistrationValues): string | null {
  if (!values.email.trim() || !values.password || !values.firstName.trim() || !values.tenantName.trim()) {
    return "Complete all required fields to continue.";
  }
  if (!EMAIL_PATTERN.test(values.email.trim())) return "Enter a valid email address.";
  if (values.password.length < 8 || values.password.length > 128) {
    return "Password must be between 8 and 128 characters.";
  }
  if (values.confirmPassword !== values.password) return "Your passwords do not match.";
  if (values.firstName.trim().length > 100 || values.lastName.trim().length > 100) {
    return "Names must be 100 characters or fewer.";
  }
  if (values.tenantName.trim().length < 2 || values.tenantName.trim().length > 150) {
    return "Workspace name must be between 2 and 150 characters.";
  }
  return null;
}
