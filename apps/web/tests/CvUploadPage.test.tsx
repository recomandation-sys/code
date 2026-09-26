import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CvUploadPage } from "../src/features/candidate-profile/pages/CvUploadPage.js";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CvUploadPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CvUploadPage", () => {
  it("renders the upload prompt", () => {
    renderPage();
    expect(screen.getByText("Upload your CV")).toBeInTheDocument();
    expect(screen.getByText("browse files")).toBeInTheDocument();
  });

  it("rejects a non-PDF file with a validation message", async () => {
    // Use fireEvent instead of userEvent.upload: userEvent enforces the
    // input's `accept` attribute and silently drops non-matching files,
    // which would never exercise the component's own validation logic.
    renderPage();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["hello"], "resume.txt", { type: "text/plain" });

    fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText("Please select a valid PDF file.")).toBeInTheDocument();
  });

  it("rejects a PDF larger than 10 MB", async () => {
    renderPage();
    const user = userEvent.setup();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const big = new File([new Uint8Array(11 * 1024 * 1024)], "resume.pdf", { type: "application/pdf" });

    await user.upload(input, big);

    expect(await screen.findByText(/larger than 10 MB/i)).toBeInTheDocument();
  });

  it("shows a Continue action once a valid PDF is selected", async () => {
    renderPage();
    const user = userEvent.setup();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["%PDF-1.4"], "resume.pdf", { type: "application/pdf" });

    await user.upload(input, file);

    expect(await screen.findByText("resume.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue" })).toBeInTheDocument();
  });
});
