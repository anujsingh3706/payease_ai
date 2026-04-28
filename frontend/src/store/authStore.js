// frontend/src/store/authStore.js

import { create } from "zustand";
import { persist } from "zustand/middleware";

const useAuthStore = create(
  persist(
    (set, get) => ({
      user:         null,
      accessToken:  null,
      refreshToken: null,
      isLoggedIn:   false,

      login: (tokenData) => {
        localStorage.setItem("access_token",  tokenData.access_token);
        localStorage.setItem("refresh_token", tokenData.refresh_token);
        set({
          user: {
            id:        tokenData.user_id,
            fullName:  tokenData.full_name,
            email:     tokenData.email,
            role:      tokenData.role,
          },
          accessToken:  tokenData.access_token,
          refreshToken: tokenData.refresh_token,
          isLoggedIn:   true,
        });
      },

      logout: () => {
        localStorage.clear();
        set({ user: null, accessToken: null, refreshToken: null, isLoggedIn: false });
      },

      updateUser: (data) => set((state) => ({
        user: { ...state.user, ...data }
      })),
    }),
    { name: "payease-auth", partialize: (s) => ({ user: s.user, isLoggedIn: s.isLoggedIn }) }
  )
);

export default useAuthStore;