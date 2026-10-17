import React from "react";

export function WhatsAppLogo({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="16" fill="#25D366" />
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M16 6C10.477 6 6 10.477 6 16C6 17.925 6.544 19.724 7.489 21.254L6.5 25.5L10.865 24.536C12.35 25.459 14.113 26 16 26C21.523 26 26 21.523 26 16C26 10.477 21.523 6 16 6ZM12.75 10.75C12.5 10.15 12.28 10.14 12.05 10.13C11.88 10.12 11.68 10.12 11.48 10.12C11.28 10.12 10.96 10.2 10.68 10.5C10.4 10.8 9.61 11.54 9.61 13.04C9.61 14.54 10.7 15.99 10.85 16.19C11 16.39 12.98 19.53 16.07 20.73C18.64 21.73 19.16 21.53 19.71 21.48C20.26 21.43 21.47 20.76 21.72 20.06C21.97 19.36 21.97 18.76 21.89 18.64C21.82 18.51 21.62 18.44 21.32 18.29C21.02 18.14 19.55 17.41 19.27 17.31C18.99 17.21 18.79 17.16 18.59 17.46C18.39 17.76 17.82 18.44 17.64 18.64C17.47 18.84 17.29 18.86 16.99 18.71C16.69 18.56 15.73 18.25 14.59 17.23C13.7 16.44 13.1 15.46 12.92 15.16C12.75 14.86 12.9 14.7 13.05 14.55C13.19 14.41 13.35 14.2 13.5 14.02C13.65 13.85 13.7 13.72 13.8 13.52C13.9 13.32 13.85 13.15 13.78 13C13.7 12.85 13.1 11.37 12.85 10.77C12.61 10.18 12.36 10.26 12.18 10.25L12.75 10.75Z"
        fill="white"
      />
    </svg>
  );
}

export function InstagramLogo({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="ig-rg-real" cx="20%" cy="105%" r="130%">
          <stop offset="0%" stopColor="#fdf497" />
          <stop offset="5%" stopColor="#fdf497" />
          <stop offset="45%" stopColor="#fd5949" />
          <stop offset="60%" stopColor="#d6249f" />
          <stop offset="90%" stopColor="#285AEB" />
        </radialGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#ig-rg-real)" />
      <rect x="8" y="8" width="16" height="16" rx="5" stroke="white" strokeWidth="2" />
      <circle cx="16" cy="16" r="4" stroke="white" strokeWidth="2" />
      <circle cx="20.5" cy="11.5" r="1.2" fill="white" />
    </svg>
  );
}

export function MessengerLogo({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="msg-lg-real" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#006AFF" />
          <stop offset="100%" stopColor="#00C6FF" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="16" fill="url(#msg-lg-real)" />
      <path
        d="M16 7C11.03 7 7 10.63 7 15.11C7 17.66 8.31 19.94 10.36 21.39V25L13.82 23.1C14.52 23.3 15.25 23.4 16 23.4C20.97 23.4 25 19.77 25 15.29C25 10.81 20.97 7 16 7ZM16.83 17.42L14.62 15.07L10.31 17.42L15.05 12.38L17.26 14.73L21.57 12.38L16.83 17.42Z"
        fill="white"
      />
    </svg>
  );
}

export function FacebookLogo({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="16" fill="#1877F2" />
      <path
        d="M18.5 16h-2.5v9h-3.8v-9h-1.8v-3.2h1.8v-2.1c0-2.5 1.5-3.9 3.8-3.9 1.1 0 2.3.2 2.3.2v2.5h-1.3c-1.2 0-1.6.8-1.6 1.6v1.7h2.8l-.4 3.2z"
        fill="white"
      />
    </svg>
  );
}

export function WebChatLogo({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="wc-lg-real" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0284c7" />
          <stop offset="100%" stopColor="#0ea5e9" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="16" fill="url(#wc-lg-real)" />
      <path
        d="M16 8C11.58 8 8 11.13 8 15C8 16.65 8.65 18.17 9.76 19.38L8.5 24L12.44 22.75C13.54 23.35 14.73 23.67 16 23.67C20.42 23.67 24 20.54 24 16.67C24 12.8 20.42 8 16 8ZM12.5 16C11.67 16 11 15.33 11 14.5C11 13.67 11.67 13 12.5 13C13.33 13 14 13.67 14 14.5C14 15.33 13.33 16 12.5 16ZM16 16C15.17 16 14.5 15.33 14.5 14.5C14.5 13.67 15.17 13 16 13C16.83 13 17.5 13.67 17.5 14.5C17.5 15.33 16.83 16 16 16ZM19.5 16C18.67 16 18 15.33 18 14.5C18 13.67 18.67 13 19.5 13C20.33 13 21 13.67 21 14.5C21 15.33 20.33 16 19.5 16Z"
        fill="white"
      />
    </svg>
  );
}

export function GoogleLogo({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}
