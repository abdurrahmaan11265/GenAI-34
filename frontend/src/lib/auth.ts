/**
 * NextAuth configuration — credentials provider delegates to FastAPI.
 *
 * The access_token returned by FastAPI is stored in the JWT and
 * forwarded in session.user.accessToken so all page-level API calls
 * can include it in the Authorization header.
 *
 * When FastAPI is not yet running (NEXT_PUBLIC_API_URL not set or unreachable),
 * the login will fail with a clear error — no silent mock auth.
 */

import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { loginUser } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        try {
          const data = await loginUser(
            credentials.email,
            credentials.password
          );

          // Shape NextAuth expects: must have at minimum { id, email, name }
          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name,
            image: data.user.avatarUrl ?? null,
            // Custom field — forwarded through JWT → session
            accessToken: data.access_token,
          };
        } catch (err) {
          // Returning null causes NextAuth to show "CredentialsSignin" error
          console.error("[auth] FastAPI login failed:", err);
          return null;
        }
      },
    }),
  ],

  callbacks: {
    /**
     * Persist the accessToken in the JWT so it survives page reloads.
     */
    async jwt({ token, user }) {
      if (user) {
        token.sub = user.id;

        token.accessToken = (user as { accessToken?: string }).accessToken;
      }
      return token;
    },

    /**
     * Expose accessToken and user.id to client-side session.
     */
    async session({ session, token }) {
      if (session.user) {
        (session.user as { id?: string }).id = token.sub ?? "";
        (session.user as { accessToken?: string }).accessToken =
          token.accessToken as string | undefined;
      }
      return session;
    },
  },

  pages: {
    signIn: "/",          // redirect unauthenticated users here
    error: "/",           // auth errors go back to landing page
  },

  session: {
    strategy: "jwt",
    maxAge: 60 * 60 * 24 * 7, // 7 days — matches typical FastAPI token expiry
  },

  secret: process.env.NEXTAUTH_SECRET,

  debug: process.env.NODE_ENV === "development",
};

/**
 * Helper to extract the access token from a NextAuth session.
 * Use this in page-level hooks to get the token for API calls.
 *
 * Example:
 *   const { data: session } = useSession();
 *   const token = getToken(session);
 */
export function getToken(session: { user?: unknown } | null): string {
  if (!session?.user) return "";
  return (session.user as { accessToken?: string }).accessToken ?? "";
}

/**
 * Helper to extract the user ID from a NextAuth session.
 */
export function getUserId(session: { user?: unknown } | null): string {
  if (!session?.user) return "";
  return (session.user as { id?: string }).id ?? "";
}

export { API_URL };
