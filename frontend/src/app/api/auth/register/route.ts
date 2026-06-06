/**
 * Registration proxy — forwards to FastAPI and then signs the user in.
 *
 * NOTE: In production this route is not strictly needed. The client could
 * call FastAPI /auth/register directly. However, having it here gives us
 * a place to add CSRF checks, rate limiting, or field normalization
 * before forwarding to FastAPI.
 */

import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name, email, password } = body;

  if (!name || !email || !password) {
    return NextResponse.json(
      { error: "name, email and password are required" },
      { status: 400 }
    );
  }

  try {
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(
        { error: data.detail ?? data.error ?? "Registration failed" },
        { status: res.status }
      );
    }

    // Return the user so the client can immediately call signIn
    return NextResponse.json({ user: data.user }, { status: 201 });
  } catch (err) {
    console.error("[register] FastAPI unreachable:", err);
    return NextResponse.json(
      { error: "Backend unavailable — please try again later" },
      { status: 503 }
    );
  }
}
