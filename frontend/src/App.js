import React, { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [formData, setFormData] = useState({
    client_name: "",
    client_email: "",
    appointment_date: "",
    appointment_time: "",
    service: "",
    notes: "",
    status: "pending",
  });

  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await axios.post("http://127.0.0.1:8000/api/appointments/", formData);
      setMessage("Appointment booked successfully!");

      setFormData({
        client_name: "",
        client_email: "",
        appointment_date: "",
        appointment_time: "",
        service: "",
        notes: "",
        status: "pending",
      });
    } catch (error) {
      console.error(error);
      setMessage("Error booking appointment.");
    }
  };

  return (
    <div className="container">
      <h1>Book an Appointment</h1>

      <form onSubmit={handleSubmit} className="booking-form">
        <input
          type="text"
          name="client_name"
          placeholder="Your Name"
          value={formData.client_name}
          onChange={handleChange}
          required
        />

        <input
          type="email"
          name="client_email"
          placeholder="Email"
          value={formData.client_email}
          onChange={handleChange}
          required
        />

        <input
          type="date"
          name="appointment_date"
          value={formData.appointment_date}
          onChange={handleChange}
          required
        />

        <input
          type="time"
          name="appointment_time"
          value={formData.appointment_time}
          onChange={handleChange}
          required
        />

        <input
          type="text"
          name="service"
          placeholder="Service"
          value={formData.service}
          onChange={handleChange}
          required
        />

        <textarea
          name="notes"
          placeholder="Notes"
          value={formData.notes}
          onChange={handleChange}
        />

        <button type="submit">Book Appointment</button>
      </form>

      {message && <p>{message}</p>}
    </div>
  );
}

export default App;