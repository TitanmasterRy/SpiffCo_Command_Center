# SpiffCo Command Center — Master Development Prompt

You are the lead software architect and principal engineer for this project.

Your task is to build a production-quality application called **SpiffCo Command Center**.

This is **not** a prototype, proof of concept, or demo. Design it as if it will eventually become an open-source application used by thousands of Satisfactory players.

---

# Mission

Create a self-hosted web application that connects to **Satisfactory** through **Ficsit Remote Monitoring (FRM)**.

The application should provide a live operations center for factories, production, logistics, power, blueprints, and world management.

Think of it as combining:

* Satisfactory Tools
* SCADA software
* Grafana
* Google Maps
* ERP software
* Blueprint management
* Production planning

under one unified interface.

---

# General Requirements

The application must be:

* Modular
* Extensible
* Well documented
* Strongly typed
* Production ready
* Easy to maintain
* Easy to test

Avoid monolithic code.

Everything should be separated into reusable modules.

---

# Recommended Tech Stack

## Frontend

React

TypeScript

Vite

TailwindCSS

React Router

TanStack Query

Zustand

Leaflet or MapLibre GL

Chart.js or Recharts

Framer Motion

---

## Backend

Python

FastAPI

Pydantic

SQLAlchemy

WebSockets

Background task scheduler

---

## Database

SQLite by default

Easy migration to PostgreSQL later

---

# Folder Structure

Implement this exact project structure.

```
SpiffCo_Command_Center/

README.md

LICENSE

CHANGELOG.md

CONTRIBUTING.md

CLAUDE.md

.env.example

docker-compose.yml

frontend/

backend/

shared/

database/

docs/

scripts/

tests/

assets/

examples/

plugins/
```

---

# Frontend Structure

```
frontend/

src/

components/

layout/

pages/

hooks/

contexts/

services/

stores/

api/

utils/

types/

theme/

icons/

styles/

assets/

tests/
```

Responsibilities:

components

Reusable UI

Buttons

Cards

Dialogs

Inputs

Tables

Notifications

layout

Navigation

Sidebar

Top bar

Footer

pages

Dashboard

Map

Factories

Blueprints

Power

Resources

Settings

Planner

Train Network

hooks

Custom React hooks

contexts

Global providers

services

Business logic

stores

Zustand state management

api

HTTP + WebSocket clients

utils

Formatting

Math

Helpers

types

Shared TypeScript types

---

# Backend Structure

```
backend/

app/

api/

services/

models/

schemas/

database/

connectors/

frm/

simulation/

planner/

analytics/

advisors/

blueprints/

resources/

power/

logistics/

world/

storage/

workers/

config/

tests/
```

Responsibilities

api

REST endpoints

services

Business logic

models

Database models

schemas

Pydantic models

database

SQLAlchemy

connectors

External integrations

frm

Ficsit Remote Monitoring integration

simulation

Offline simulation

planner

Production planner

analytics

Metrics

Efficiency

Historical data

advisors

Factory advisor engine

blueprints

Blueprint recognition

resources

Node management

power

Power grid calculations

logistics

Trains

Belts

Pipes

Drones

workers

Background tasks

---

# Shared Folder

```
shared/

types/

constants/

recipes/

schemas/

icons/
```

Contains data shared by frontend and backend.

---

# Database

Create JSON data files for:

recipes

buildings

items

resources

alternate recipes

build costs

power buildings

transportation

resource nodes

machine definitions

---

# Documentation

Create:

Architecture

API reference

Database schema

Developer guide

Deployment guide

Plugin guide

Coding standards

Contribution guide

Roadmap

Known limitations

---

# Phase 1

Foundation

Create:

authentication layer (optional)

configuration

logging

error handling

API framework

database

WebSocket server

---

# Phase 2

Dashboard

Display:

Factory status

Power

Production

Storage

Alerts

Efficiency

Machine counts

Graphs

---

# Phase 3

World Map

Interactive map

Player position

Factories

Resource nodes

Trains

Drone ports

Truck stations

Power plants

Custom markers

Search

Filters

Layers

---

# Phase 4

Factory Planner

Grid designer

Building placement

Blueprint editor

Area planning

Import/export

Versioning

---

# Phase 5

Production Planner

Recipes

Clock speed

Somersloops

Overclocking

Underclocking

Alternate recipes

Input/output balancing

Power calculations

Material requirements

Shopping list generation

---

# Phase 6

Logistics

Belts

Pipes

Trains

Truck routes

Drone routes

Flow visualization

Throughput analysis

---

# Phase 7

Power

Power graph

Historical usage

Consumption

Generation

Battery backup

Recommendations

---

# Phase 8

Blueprint System

Blueprint library

Categories

Tags

Search

Favorites

Import

Export

Statistics

---

# Phase 9

Analytics

Historical graphs

Machine uptime

Production history

Power history

Resource consumption

Factory comparisons

KPIs

---

# Phase 10

AI Advisor

Detect:

Resource shortages

Power shortages

Belt bottlenecks

Pipe bottlenecks

Machine starvation

Idle machines

Storage overflow

Suggest:

Clock speed changes

Additional miners

More generators

Better recipes

Train improvements

Factory expansion

Provide explanations for every recommendation.

---

# Phase 11

Ficsit Remote Monitoring Integration

Create a dedicated connector.

Support:

Automatic discovery

Reconnect

Health monitoring

Caching

WebSockets

Polling fallback

Normalize FRM data into internal models.

Never expose raw FRM responses directly to the frontend.

---

# Phase 12

Offline Mode

If FRM is unavailable:

Read save files

Provide planning tools

Blueprint editing

Recipe calculations

Material tracking

---

# Code Quality

Every public function must have documentation.

Write unit tests.

Avoid duplicated logic.

Keep components small.

Prefer composition over inheritance.

Use dependency injection where appropriate.

Avoid global mutable state.

---

# User Experience

Dark mode first.

Responsive layout.

Keyboard shortcuts.

Search everywhere.

Fast loading.

Smooth animations.

Professional industrial aesthetic inspired by Satisfactory.

---

# Deliverables

Work incrementally.

At the end of every milestone:

* Update documentation.
* Add tests.
* Explain architectural decisions.
* Refactor where necessary.
* Keep the project buildable at all times.

Do not skip ahead. Complete each phase before starting the next.

If a design decision is uncertain, document the trade-offs before implementing it.
