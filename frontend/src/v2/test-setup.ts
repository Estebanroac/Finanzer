// Testing Library solo limpia el DOM entre tests por sí sola si Vitest expone globals;
// aquí no los usamos, así que se desmonta explícitamente tras cada test.
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => cleanup());
