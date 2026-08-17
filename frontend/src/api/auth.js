import client from "./client";

export async function signupUser(data) {
  const response = await client.post("/auth/signup", data);
  return response.data;
}

export async function loginUser(data) {
  const response = await client.post("/auth/login", data);
  return response.data;
}

export async function getCurrentUser() {
  const response = await client.get("/auth/me");
  return response.data.user;
}