# Keep Owner contact inside Conversations

Buyer-to-Owner contact occurs only through a Conversation about a Property. Owner email, phone, and identity details are not exposed on Property pages; the redundant `phone_number` and `cnic` fields are removed from Property rather than treating sensitive Owner data as listing attributes.

## Consequences

- Property creation asks only for information needed to describe and publish the Property.
- Any future Owner identity verification must be modeled separately from Property and designed with an explicit privacy lifecycle.
